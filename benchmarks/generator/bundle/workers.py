"""Nine deterministic, capability-aware Agent workers and external worker SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.bundle.artifacts import AgentArtifact
from generator.bundle.compiler import resolve_assets
from generator.bundle.coordinator import AgentTask, BenchmarkCoordinator, TaskHandler
from generator.bundle.fault_profiles import (
    build_bundle_fault_candidate, supported_bundle_faults,
)
from generator.bundle.request import BenchmarkRequest
from generator.bundle.composer import compose_fault_candidates
from generator.bundle.templates import (
    ApplicationTemplate, ApplicationTemplateRegistry, builtin_template_registry,
)


def _fingerprints(inputs: Sequence[AgentArtifact]) -> Tuple[str, ...]:
    return tuple(item.artifact_fingerprint for item in inputs)


def _artifact(task: AgentTask, inputs, payload) -> AgentArtifact:
    return AgentArtifact(
        artifact_type=task.output_artifact_type,
        artifact_id=task.output_artifact_id,
        producer=task.agent_role, payload=payload,
        input_fingerprints=_fingerprints(inputs),
    )


def _address(asset: Mapping[str, Any]) -> str:
    interface = next(
        (item for item in asset.get("interfaces", ()) if item.get("name") == "lan0"),
        None,
    )
    if not interface:
        raise ValueError(f"asset {asset.get('container')} has no lan0 address")
    return str(interface["address"]).split("/")[0]


@dataclass(frozen=True)
class WorkerContext:
    request: BenchmarkRequest
    capabilities: Mapping[str, Any]
    templates: ApplicationTemplateRegistry

    @classmethod
    def build(
        cls, request: BenchmarkRequest, capabilities: Mapping[str, Any],
        templates: ApplicationTemplateRegistry | None = None,
    ) -> "WorkerContext":
        if capabilities.get("topology_id") != request.topology_id:
            raise ValueError("worker capabilities target another topology")
        registry = templates or builtin_template_registry()
        for template_id in (*request.applications, request.observer_template):
            registry.require(template_id)
        return cls(request, dict(capabilities), registry)

    def template(self, template_id: str) -> ApplicationTemplate:
        return self.templates.require(template_id)

    def asset(self, template_id: str) -> Mapping[str, Any]:
        template = self.template(template_id)
        return resolve_assets(
            {"software": template.software_id, "choose": 1}, self.capabilities
        )[0]


def _fault_composition(context: WorkerContext):
    request, candidates, errors = context.request, [], []
    supported = set(supported_bundle_faults())
    if request.fault_types:
        missing = set(request.fault_types) - supported
        if missing:
            raise ValueError(
                f"faults have no formal Bundle profiles: {sorted(missing)}; "
                f"supported={sorted(supported)}"
            )
    protected = (str(context.asset(request.observer_template)["container"]),)
    for index, template_id in enumerate(request.applications):
        template, target = context.template(template_id), context.asset(template_id)
        allowed = tuple(request.fault_types or template.suggested_faults)
        for offset, fault_type in enumerate(allowed):
            try:
                candidates.append(build_bundle_fault_candidate(
                    fault_type=fault_type, template_id=template_id,
                    preferred_container=str(target["container"]),
                    sequence=index + offset, seed=request.seed,
                    manifest=context.capabilities, protected_assets=protected,
                ))
            except ValueError as exc:
                errors.append(str(exc))
    if len(candidates) < request.fault_count:
        detail = "; ".join(sorted(set(errors))) or "no compatible capability binding"
        raise ValueError(
            f"only {len(candidates)}/{request.fault_count} safely automated "
            f"Bundle faults are available: {detail}"
        )
    return compose_fault_candidates(
        candidates, request, context.capabilities,
        protected_asset=protected[0],
    )


def _selected_faults(context: WorkerContext) -> Tuple[Mapping[str, Any], ...]:
    return _fault_composition(context).candidates


class TopologyAgentWorker:
    role = "topology_agent"

    def __init__(self, context: WorkerContext): self.context = context

    def __call__(self, task, inputs):
        return _artifact(task, inputs, {"topology_id": self.context.request.topology_id})


class SoftwareAgentWorker:
    role = "software_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        software = [
            self.context.template(item).software_id
            for item in (*self.context.request.applications,
                         self.context.request.observer_template)
        ]
        return _artifact(task, inputs, {"required_software": list(dict.fromkeys(software))})


class ServiceAgentWorker:
    role = "service_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        services = []
        for template_id in self.context.request.applications:
            template = self.context.template(template_id)
            asset = self.context.asset(template_id)
            services.append({
                "schema_version": 1,
                "service_id": f"{template_id}_service",
                "driver": "service.process",
                "selector": {"container": asset["container"]},
                "capabilities_required": [template.capability],
                "ports": [template.port],
                "parameters": {
                    "start_argv": list(template.start_argv),
                    "health_argv": list(template.health_argv),
                },
            })
        return _artifact(task, inputs, {"services": services})


class WorkloadAgentWorker:
    role = "workload_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        observer = self.context.asset(self.context.request.observer_template)
        workloads = []
        for template_id in self.context.request.applications:
            template, target = self.context.template(template_id), self.context.asset(template_id)
            source = target if template.source_mode == "service" else observer
            address = "127.0.0.1" if template.source_mode == "service" else _address(target)
            workloads.append({
                "schema_version": 1, "workload_id": f"{template_id}_workload",
                "driver": template.workload_driver,
                "source": {"container": source["container"]},
                "target_service": f"{template_id}_service",
                "parameters": template.parameters(address),
                "duration_seconds": 1,
            })
        return _artifact(task, inputs, {"workloads": workloads})


class FaultAgentWorker:
    role = "fault_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        request = self.context.request
        composition = _fault_composition(self.context)
        return _artifact(task, inputs, {
            "relationship": composition.relationship,
            "faults": [item.to_dict() for item in composition.specs],
        })


class TestAgentWorker:
    role = "test_agent"

    def __init__(self, context): self.context = context

    def _protocol_test(self, template_id, phase, expected_failure=False):
        template, target = self.context.template(template_id), self.context.asset(template_id)
        observer = self.context.asset(self.context.request.observer_template)
        source = target if template.source_mode == "service" else observer
        address = "127.0.0.1" if template.source_mode == "service" else _address(target)
        return {
            "schema_version": 1, "test_id": f"{phase}_{template_id}",
            "phase": phase, "driver": template.probe_driver,
            "selector": {"container": source["container"]},
            "parameters": template.parameters(address),
            "assertion": {
                "kind": "exit_code_not" if expected_failure else "exit_code",
                "value": 0,
            },
            "expectation_id": (
                f"{template_id}_availability" if phase != "baseline"
                else f"{template_id}_healthy"
            ),
            "retries": 5 if phase == "recovery" else 1,
        }

    def __call__(self, task, inputs):
        request = self.context.request
        selected = _selected_faults(self.context)
        faulted = {
            str(item["template_id"]) for item in selected
            if item.get("breaks_application")
        }
        tests = [
            self._protocol_test(item, "baseline") for item in request.applications
        ]
        tests.extend(
            self._protocol_test(item, "active", expected_failure=item in faulted)
            for item in request.applications
        )
        observer = self.context.asset(request.observer_template)
        tests.append({
            "schema_version": 1, "test_id": "active_observer", "phase": "active",
            "driver": "probe.container", "selector": {"container": observer["container"]},
            "parameters": {}, "assertion": {"kind": "equals", "value": "true"},
            "expectation_id": "observer_availability",
        })
        # Recovery is semantic only if every declared application is healthy;
        # testing only directly faulted applications misses routing pollution.
        tests.extend(
            self._protocol_test(item, "recovery")
            for item in request.applications
        )
        for index, candidate in enumerate(selected):
            probe = candidate.get("probe")
            if not probe:
                continue
            identity = f"fault_{index + 1:02d}_{candidate['template_id']}"
            expectation = str(candidate["must_break"][0])
            for phase in ("baseline", "active", "recovery"):
                tests.append({
                    "schema_version": 1,
                    "test_id": f"{phase}_{identity}",
                    "phase": phase,
                    "driver": probe["driver"],
                    "selector": dict(probe["selector"]),
                    "parameters": dict(probe["parameters"]),
                    "assertion": dict(probe[f"{phase}_assertion"]),
                    "expectation_id": (
                        f"{identity}_healthy" if phase == "baseline" else expectation
                    ),
                    "retries": 5 if phase == "recovery" else 1,
                })
        return _artifact(task, inputs, {"tests": tests})


class OracleAgentWorker:
    role = "oracle_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        tests = TestAgentWorker(self.context)(task, ()).payload["tests"]
        active = [item["test_id"] for item in tests if item["phase"] == "active"]
        recovery = [item["test_id"] for item in tests if item["phase"] == "recovery"]
        required = active + recovery
        return _artifact(task, inputs, {"oracles": [{
            "schema_version": 1, "oracle_id": "generated_oracle_v1",
            "required_tests": required,
            "phase_requirements": {"active": active, "recovery": recovery},
        }]})


class ScoringAgentWorker:
    role = "scoring_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        selected = _selected_faults(self.context)
        must_break = {value for item in selected for value in item["must_break"]}
        tests = TestAgentWorker(self.context)(task, ()).payload["tests"]
        weights = {
            item["test_id"]: (2.0 if item["expectation_id"] in must_break else 1.0)
            for item in tests if item["phase"] in {"active", "recovery"}
        }
        return _artifact(task, inputs, {"scoring": [{
            "schema_version": 1, "scoring_id": "generated_weighted_v1",
            "weights": weights, "pass_threshold": 1.0,
        }]})


class SafetyReviewerAgentWorker:
    role = "safety_reviewer_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        expected = {
            "topology_ref", "software", "service", "workload", "fault_set",
            "test", "oracle", "scoring",
        }
        if {item.artifact_type for item in inputs} != expected:
            raise ValueError("safety reviewer did not receive the complete artifact set")
        return _artifact(task, inputs, {"policies": [{}]})


WORKER_TYPES = (
    TopologyAgentWorker, SoftwareAgentWorker, ServiceAgentWorker,
    WorkloadAgentWorker, FaultAgentWorker, TestAgentWorker,
    OracleAgentWorker, ScoringAgentWorker, SafetyReviewerAgentWorker,
)


def builtin_worker_handlers(context: WorkerContext) -> Dict[str, TaskHandler]:
    return {worker_type.role: worker_type(context) for worker_type in WORKER_TYPES}


def run_external_worker_once(
    coordinator: BenchmarkCoordinator, context: WorkerContext,
    *, role: str, worker_id: str,
) -> Dict[str, Any]:
    handler = builtin_worker_handlers(context).get(role)
    if handler is None:
        raise ValueError(f"unknown built-in worker role={role}")
    claim = coordinator.claim_next(worker_id=worker_id, agent_role=role)
    if claim is None:
        return {"status": "idle", "role": role, "worker_id": worker_id}
    task = AgentTask.from_dict(claim["task"])
    inputs = tuple(AgentArtifact.from_dict(x) for x in claim["input_artifacts"])
    try:
        artifact = handler(task, inputs)
        path = coordinator.complete_claim(task.task_id, claim["lease_id"], artifact)
    except Exception as exc:
        coordinator.fail_claim(task.task_id, claim["lease_id"], str(exc))
        raise
    return {
        "status": "complete", "role": role, "worker_id": worker_id,
        "task_id": task.task_id, "artifact": str(path),
        "artifact_fingerprint": artifact.artifact_fingerprint,
    }
