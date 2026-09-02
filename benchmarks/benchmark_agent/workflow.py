"""Scenario-driven runtime benchmark qualification, evaluation, and cleanup."""

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark_agent.api import invoke_tool, wait_for_service
from benchmark_agent.control import (
    create_candidate_grant_contract,
    create_session_contract,
)
from benchmark_agent.evaluation import run_candidate_evaluation, wait_for_adapter
from benchmark_agent.faults import verify_evidence_drift
from benchmark_agent.journal import Journal
from benchmark_agent.models import (
    BenchmarkPlan,
    BenchmarkRequest,
    EvaluationRecord,
    ExecutionEvent,
    FaultCapabilityBinding,
    RuntimeBenchmarkBundle,
    RuntimeContext,
)
from benchmark_agent.scenario import Scenario

ActionProvider = Callable[[list[dict[str, str]]], tuple[dict[str, str], dict[str, Any]]]
EvaluationRunner = Callable[..., tuple[list[dict[str, Any]], dict[str, Any]]]


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_request(scenario: Scenario) -> BenchmarkRequest:
    if scenario.topology.mode == "runtime_discovered":
        topology_source = {
            "mode": "runtime_discovered",
            "compose_project": scenario.project,
            "interpretation": scenario.topology.interpretation,
            "example_role": "runtime-discovered Compose project binding, not a hard-coded topology",
        }
    elif scenario.topology.mode == "python_discovered":
        topology_source = {
            "mode": "python_discovered",
            "script_path": scenario.topology.script_path,
            "descriptor_fingerprint": scenario.topology.descriptor_fingerprint,
            "artifact_id": scenario.topology.artifact_id,
            "compose_path": scenario.topology.compose_path,
            "interpretation": scenario.topology.interpretation,
            "compose_project": scenario.project,
            "source_role": "auto-discovered SEED Python topology",
        }
    return BenchmarkRequest(
        topology_source=topology_source,
        objective=f"Evaluate diagnosis and repair of a {scenario.fault.kind} in a runtime node.",
        fault=scenario.fault.model_dump(),
        seed=scenario.seed,
    )


def compile_plan(
    request: BenchmarkRequest, context: RuntimeContext, scenario: Scenario
) -> BenchmarkPlan:
    draft = {
        "schema_version": 1,
        "state": "approved",
        "request": request.model_dump(),
        "runtime": context.model_dump(),
        "lifecycle": [
            {"stage": "baseline", "tool": scenario.fault.probe_tool},
            {"stage": "inject", "tool": scenario.fault.inject_tool},
            {"stage": "fault_verify", "tool": scenario.fault.probe_tool},
            {"stage": "author_recover", "tool": scenario.fault.recover_tool},
            {"stage": "recovery_verify", "tool": scenario.fault.probe_tool},
            {"stage": "candidate_evaluate", "adapter_tools": scenario.capabilities},
            {"stage": "cleanup", "tool": scenario.fault.recover_tool},
        ],
    }
    draft["fingerprint"] = _fingerprint(draft)
    return BenchmarkPlan.model_validate(draft)


def _default_provider(scenario: Scenario) -> ActionProvider:
    from benchmark_agent.config import BenchmarkConfig
    from benchmark_agent.providers.openai_compat import OpenAICompatibleProvider

    candidate = BenchmarkConfig.load().candidate
    key = os.environ.get(candidate.api_key_env)
    if not key:
        raise ValueError(f"{candidate.api_key_env} is required for the native runtime")
    return OpenAICompatibleProvider(
        base_url=candidate.base_url,
        api_key=key,
        model=candidate.model,
        name=candidate.provider_name,
        allowed_actions=set(scenario.allowed_actions),
    ).decide


def _start_adapter(
    grant_spec_path: Path, port: int, log_path: Path
) -> subprocess.Popen:
    """Run the sandbox Adapter as a separate service process (development mode)."""

    adapter_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["BENCHMARK_GRANT_SPEC"] = str(grant_spec_path)
    env["PYTHONPATH"] = str(adapter_root) + os.pathsep + env.get("PYTHONPATH", "")
    interpreter = env.get("BENCHMARK_ADAPTER_PYTHON", sys.executable)
    command = [
        interpreter,
        "-m",
        "benchmark_adapter",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    handle = log_path.open("a", encoding="utf-8")
    return subprocess.Popen(command, env=env, stdout=handle, stderr=handle)


def run_runtime_benchmark(
    *,
    api_url: str,
    output_root: Path,
    project: str | None = None,
    materialize: bool = True,
    cleanup_topology: bool = True,
    candidate_provider: ActionProvider | None = None,
    evaluation_runner: EvaluationRunner | None = None,
    adapter_port: int = 8101,
    candidate_runtime: str = "native",
    inspect_model: str | None = None,
    inspect_base_url: str | None = None,
    scenario: Scenario | None = None,
) -> Path:
    if scenario is None:
        raise ValueError("an explicit scenario is required")
    is_python_discovered = scenario.topology.mode == "python_discovered"
    is_runtime_discovered = scenario.topology.mode == "runtime_discovered"
    if is_runtime_discovered and project is not None and project != scenario.project:
        raise ValueError(
            "runtime-discovered scenarios must keep the discovered project binding"
        )
    project = project or scenario.project
    # A runtime-discovered scenario binds an already-running project: it never
    # materializes a topology, regardless of the caller's materialize flag.
    materialize = materialize and not is_runtime_discovered
    output_root.mkdir(parents=True, exist_ok=True)
    session = datetime.now(UTC).strftime(
        f"{scenario.naming.session_prefix}_%Y%m%dT%H%M%SZ"
    )
    output = output_root / session
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output / "journal.jsonl")
    api_trace: list[dict[str, Any]] = []
    request = build_request(scenario)
    _write(output / "scenario.json", scenario.model_dump())
    _write(output / "request.json", request.model_dump())
    target = request.fault["target_service"]
    operation_binding = (
        FaultCapabilityBinding.model_validate(scenario.capability_binding)
        if scenario.capability_binding is not None
        else None
    )

    def probe() -> dict[str, Any]:
        return call(
            scenario.fault.probe_tool,
            {"project": project, "service": target, **scenario.fault.probe_arguments},
        )

    def is_expected_probe(result: dict[str, Any], expected: bool) -> bool:
        return result.get(scenario.fault.healthy_field) is expected

    def inject(suffix: str) -> dict[str, Any]:
        if operation_binding is not None:
            return call(
                operation_binding.inject_operation["tool"],
                {
                    "project": project,
                    "service": target,
                    **operation_binding.inject_operation["arguments"],
                },
            )
        return call(
            scenario.fault.inject_tool,
            {
                "project": project,
                "service": target,
                "session_id": session,
                "idempotency_key": f"{session}-{suffix}",
                **scenario.fault.inject_arguments,
            },
        )

    def recover(token: str) -> dict[str, Any]:
        if operation_binding is not None:
            result = call(
                operation_binding.recovery_operation["tool"],
                {
                    "project": project,
                    "service": target,
                    **operation_binding.recovery_operation["arguments"],
                },
            )
            return {**result, "recovered": result.get("exit_code", 0) == 0}
        return call(
            scenario.fault.recover_tool,
            {
                "project": project,
                "service": target,
                "session_id": session,
                "recovery_token": token,
            },
        )

    def call(
        name: str, arguments: dict[str, Any], timeout: int = 300
    ) -> dict[str, Any]:
        receipt = invoke_tool(api_url, name, arguments, timeout=timeout)
        api_trace.append(receipt)
        return receipt["result"]

    def topology_action(action: str) -> dict[str, Any]:
        if is_python_discovered:
            return call(
                "benchmark.topology.lifecycle",
                {
                    "action": action,
                    "artifact_id": scenario.topology.artifact_id,
                    "compose_path": scenario.topology.compose_path,
                    "project": project,
                },
                timeout=2200,
            )
        raise RuntimeError(
            "runtime-discovered topology has no materialization lifecycle"
        )

    def event(kind: str, status: str, data: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schema_version": 1,
            "sequence": len(journal.events),
            "kind": kind,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
            "ai_invoked": False,
        }
        body["fingerprint"] = _fingerprint(body)
        event_body = ExecutionEvent.model_validate(body).model_dump()
        journal.append(event_body)
        return event_body

    recovery_token: str | None = None
    adapter_process: subprocess.Popen | None = None
    cleanup: dict[str, Any] = {"topology_down": False, "fault_recovered": False}
    try:
        wait_for_service(api_url)
        if materialize:
            actions = ["build", "up", "readiness"]
            for action in actions:
                result = topology_action(action)
                event(
                    f"topology_{action}",
                    "passed" if result["successful"] else "failed",
                    result,
                )
                if not result["successful"]:
                    raise RuntimeError(f"topology {action} failed")

        if scenario.capability_binding is not None:
            current_evidence = call(
                "benchmark.runtime.service_capabilities",
                {"project": project, "service": target},
            )
            binding = FaultCapabilityBinding.model_validate(scenario.capability_binding)
            verify_evidence_drift(binding, current_evidence)
            event("capability_drift_check", "passed", current_evidence)

        inventory = call("benchmark.runtime.describe", {"project": project})
        _write(
            output / "session_contract.json",
            create_session_contract(session, project, target, inventory),
        )
        if not any(
            item["service"] == target and item["status"] == "running"
            for item in inventory["services"]
        ):
            raise RuntimeError(
                f"target service {target!r} is not running in project {project!r}"
            )

        baseline = probe()
        if not is_expected_probe(baseline, scenario.fault.baseline_value):
            raise RuntimeError(
                f"{scenario.id} baseline probe did not match expectation"
            )
        event("baseline", "passed", baseline)

        if is_python_discovered:
            provenance = {
                "source": request.topology_source,
                "descriptor_fingerprint": scenario.topology.descriptor_fingerprint,
                "inventory_fingerprint": _fingerprint(inventory),
            }
        else:
            provenance = {
                "source": request.topology_source,
                "inventory_fingerprint": _fingerprint(inventory),
            }
        context = RuntimeContext(
            project=project,
            target_service=target,
            topology=provenance,
            inventory=inventory,
            baseline=baseline,
            capabilities=scenario.capabilities,
        )
        plan = compile_plan(request, context, scenario)
        _write(output / "runtime_context.json", context.model_dump())
        _write(output / "approved_plan.json", plan.model_dump())

        injected = inject("qualification")
        recovery_token = injected.get("recovery_token", "local-operation-recovery")
        event(
            "qualification_inject",
            "passed",
            {k: v for k, v in injected.items() if k != "recovery_token"},
        )

        failed_probe = probe()
        if not is_expected_probe(failed_probe, scenario.fault.fault_value):
            raise RuntimeError(
                f"{scenario.id} fault did not create the expected probe state"
            )
        event("qualification_fault_verify", "passed", failed_probe)

        recovered = recover(recovery_token)
        recovery_token = None
        recovery_probe = probe()
        if not recovered["recovered"] or not is_expected_probe(
            recovery_probe, scenario.fault.baseline_value
        ):
            raise RuntimeError("author recovery qualification failed")
        event("qualification_recovery", "passed", recovery_probe)

        injected = inject("evaluation")
        recovery_token = injected.get("recovery_token", "local-operation-recovery")
        evaluation_fault = probe()
        if not is_expected_probe(evaluation_fault, scenario.fault.fault_value):
            raise RuntimeError("evaluation fault did not reproduce")

        local_grant = create_candidate_grant_contract(session, scenario)
        _write(output / "candidate_grant_contract.json", local_grant)
        grant = local_grant
        qualification = {
            "passed": True,
            "baseline": baseline,
            "fault_probe": failed_probe,
            "recovery_probe": recovery_probe,
        }
        agent_view = {
            "objective": scenario.prompts.agent_view_objective,
            "project_alias": scenario.naming.project_alias,
            "service": target,
            "symptom": {
                "fault_kind": scenario.fault.kind,
                scenario.fault.healthy_field: scenario.fault.fault_value,
            },
        }
        bundle = RuntimeBenchmarkBundle(
            benchmark_id=session,
            plan=plan.model_dump(),
            agent_view=agent_view,
            capability_grant={
                "allowed_actions": scenario.allowed_actions,
                "target_service": target,
                "max_calls": grant["max_calls"],
                "enforced_by": "candidate_adapter",
            },
            qualification=qualification,
            evidence_fingerprints=[item["fingerprint"] for item in journal.events],
        )
        _write(output / "bundle.json", bundle.model_dump())

        grant_spec_path = output / "grant_spec.json"
        _write(
            grant_spec_path,
            {
                "agent_view": agent_view,
                "allowed_actions": scenario.allowed_actions,
                "actions": {
                    name: spec.model_dump() for name, spec in scenario.actions.items()
                },
                "terminal_action": scenario.finish_action,
                "target_service": target,
                "project": project,
                "probe_arguments": scenario.fault.probe_arguments,
                "max_calls": grant["max_calls"],
                "benchmark_id": session,
                "tool_service_url": api_url,
                "trace_path": str(output / "adapter_trace.jsonl"),
            },
        )

        if evaluation_runner is not None:
            trace, provider_metadata = evaluation_runner(
                agent_view=agent_view,
                max_calls=grant["max_calls"],
            )
        else:
            adapter_url = f"http://127.0.0.1:{adapter_port}"
            adapter_process = _start_adapter(
                grant_spec_path, adapter_port, output / "adapter.log"
            )
            wait_for_adapter(adapter_url)
            if candidate_runtime == "inspect":
                from benchmark_agent.config import BenchmarkConfig
                from benchmark_agent.inspect_runner import (
                    run_inspect_candidate_evaluation,
                )

                config = BenchmarkConfig.load()
                trace, provider_metadata = run_inspect_candidate_evaluation(
                    adapter_url=adapter_url,
                    agent_view=agent_view,
                    log_dir=output / "inspect_logs",
                    scenario=scenario,
                    model=inspect_model or config.inspect_model,
                    base_url=inspect_base_url or config.candidate.base_url,
                    api_key_env=config.candidate.api_key_env,
                    max_calls=grant["max_calls"],
                )
            elif candidate_runtime == "native":
                provider = candidate_provider or _default_provider(scenario)
                trace, provider_metadata = run_candidate_evaluation(
                    adapter_url=adapter_url,
                    provider=provider,
                    agent_view=agent_view,
                    max_calls=grant["max_calls"],
                    system_prompt=scenario.prompts.native_system,
                )
            else:
                raise ValueError(f"unsupported candidate runtime: {candidate_runtime}")

        final_probe = probe()
        violations = [
            item for item in trace if item.get("observation", {}).get("rejected")
        ]
        scoring = scenario.scoring
        score = {
            "passed": is_expected_probe(final_probe, scenario.fault.baseline_value)
            and not violations,
            "task_success": scoring.task_success
            if is_expected_probe(final_probe, scenario.fault.baseline_value)
            else 0,
            "authorization": 0 if violations else scoring.authorization,
            "efficiency": max(
                0,
                scoring.efficiency
                - max(0, len(trace) - scoring.base_turns) * scoring.penalty_per_turn,
            ),
            "total": 0,
        }
        score["total"] = (
            score["task_success"] + score["authorization"] + score["efficiency"]
        )

        cleanup_result = recover(recovery_token)
        recovery_token = None
        cleanup["fault_recovered"] = cleanup_result["recovered"]
        if materialize and cleanup_topology and not cleanup["topology_down"]:
            try:
                result = topology_action("down")
                cleanup["topology_down"] = result["successful"]
            except Exception as error:  # noqa: BLE001
                cleanup["topology_down_error"] = str(error)
        evaluation = EvaluationRecord(
            benchmark_id=session,
            provider={
                "name": provider_metadata.get("name", "unknown"),
                "model": provider_metadata.get("model"),
                "usage": provider_metadata.get("usage", {}),
                "request_id": provider_metadata.get("request_id"),
            },
            api_trace=trace,
            final_probe=final_probe,
            score_report=score,
            cleanup=cleanup,
        )
        _write(output / "events.json", journal.events)
        _write(output / "tool_service_trace.json", api_trace)
        _write(output / "evaluation.json", evaluation.model_dump())
        return output
    finally:
        if adapter_process is not None:
            try:
                adapter_process.terminate()
                adapter_process.wait(timeout=10)
            except Exception as error:  # noqa: BLE001
                cleanup["adapter_stop_error"] = str(error)
        if recovery_token:
            try:
                recover(recovery_token)
                cleanup["fault_recovered"] = True
            except Exception as error:  # noqa: BLE001
                cleanup["fault_recovery_error"] = str(error)
        if materialize and cleanup_topology:
            try:
                result = topology_action("down")
                cleanup["topology_down"] = result["successful"]
            except Exception as error:  # noqa: BLE001
                cleanup["topology_down_error"] = str(error)
        if output.exists():
            journal.write_summary(output / "events.json")
            _write(output / "cleanup.json", cleanup)
