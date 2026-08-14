"""Nine deterministic, capability-aware Agent workers and external worker SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.bundle.artifacts import AgentArtifact
from generator.bundle.compiler import resolve_assets
from generator.bundle.coordinator import AgentTask, BenchmarkCoordinator, TaskHandler
from generator.bundle.request import BenchmarkRequest
from generator.bundle.quality import select_fault_combination
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


def _selected_faults(context: WorkerContext) -> Tuple[Mapping[str, Any], ...]:
    request, candidates = context.request, []
    for index, template_id in enumerate(request.applications):
        template, target = context.template(template_id), context.asset(template_id)
        allowed = tuple(
            item for item in (request.fault_types or template.suggested_faults)
            if item in {"container.stopped", "network.netem"}
        )
        if not allowed:
            raise ValueError(f"no safely automated fault for template={template_id}")
        fault_type = allowed[index % len(allowed)]
        candidates.append({
            "candidate_id": f"{template_id}.{fault_type}",
            "template_id": template_id, "fault_type": fault_type,
            "asset": target["container"],
            "must_break": [f"{template_id}_availability"],
        })
    return select_fault_combination(candidates, request.fault_count)


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
        protected = str(self.context.asset(request.observer_template)["container"])
        faults = []
        for index, candidate in enumerate(_selected_faults(self.context)):
            template_id = str(candidate["template_id"])
            template, target = self.context.template(template_id), self.context.asset(template_id)
            fault_type = str(candidate["fault_type"])
            parameters = (
                {"interface": "lan0", "loss_percent": 100}
                if fault_type == "network.netem" else {}
            )
            expectation = f"{template_id}_availability"
            faults.append({
                "schema_version": 1,
                "fault_id": f"fault_{index + 1:02d}_{template_id}",
                "fault_type": fault_type,
                "selector": {"container": target["container"]},
                "parameters": parameters,
                "expectations": {
                    "must_break": [expectation],
                    "must_preserve": ["observer_availability"],
                },
                "safety": {
                    "max_affected_assets": request.fault_count,
                    "max_affected_asns": request.fault_count,
                    "protected_assets": [protected], "require_recovery": True,
                },
                "seed": f"{request.seed}:{template_id}:{index}",
                "schedule": {"at_seconds": 0, "duration_seconds": 0},
            })
        relationship = "single" if len(faults) == 1 else "independent"
        return _artifact(task, inputs, {"relationship": relationship, "faults": faults})


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
        faulted = {str(item["template_id"]) for item in _selected_faults(self.context)}
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
        tests.extend(self._protocol_test(item, "recovery") for item in faulted)
        return _artifact(task, inputs, {"tests": tests})


class OracleAgentWorker:
    role = "oracle_agent"

    def __init__(self, context): self.context = context

    def __call__(self, task, inputs):
        faulted = tuple(
            str(item["template_id"]) for item in _selected_faults(self.context)
        )
        active = [f"active_{item}" for item in self.context.request.applications]
        active.append("active_observer")
        recovery = [f"recovery_{item}" for item in faulted]
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
        faulted = tuple(
            str(item["template_id"]) for item in _selected_faults(self.context)
        )
        weights = {f"active_{item}": 2.0 for item in faulted}
        weights.update({f"recovery_{item}": 2.0 for item in faulted})
        weights["active_observer"] = 1.0
        for item in (x for x in self.context.request.applications if x not in faulted):
            weights[f"active_{item}"] = 1.0
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
