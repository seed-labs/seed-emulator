"""Deterministic compilation from BenchmarkIntent to existing generator inputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict

from generator.bundle.request import BenchmarkRequest
from generator.nl.catalog import CapabilityCatalog
from generator.nl.models import BenchmarkIntent
from generator.topology.models import TopologyRequest


def _sha(value: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _resource_class(scale: int) -> str:
    if scale <= 20:
        return "small"
    if scale <= 100:
        return "medium"
    if scale <= 1000:
        return "large"
    return "xlarge"


@dataclass(frozen=True)
class CompiledNaturalLanguagePlan:
    intent: BenchmarkIntent
    topology_request: TopologyRequest
    benchmark_request: BenchmarkRequest
    preview: Dict[str, Any]
    plan_fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "topology_request": self.topology_request.to_dict(),
            "benchmark_request": self.benchmark_request.to_dict(),
            "preview": self.preview,
            "plan_fingerprint": self.plan_fingerprint,
        }


def compile_intent(
    intent: BenchmarkIntent, catalog: CapabilityCatalog,
) -> CompiledNaturalLanguagePlan:
    topology = (
        catalog.topology(intent.topology_id)
        if intent.topology_id
        else catalog.select_topology(
            intent.applications, observer_required=intent.observer_required, scale=intent.scale
        )
    )
    if topology is None:
        raise ValueError("no compiled topology satisfies the normalized intent")
    missing_apps = set(intent.applications) - set(topology["application_templates"])
    if missing_apps:
        raise ValueError(f"topology lacks application capabilities: {sorted(missing_apps)}")
    unknown_faults = set(intent.fault_types) - set(catalog.fault_ids)
    if unknown_faults:
        raise ValueError(f"intent references unknown fault plugins: {sorted(unknown_faults)}")
    if not intent.difficulty or intent.fault_count < 1:
        raise ValueError("intent is not complete enough to compile")
    if intent.fault_count > len(intent.applications):
        raise ValueError("fault count exceeds selected applications")

    topology_request = TopologyRequest.from_dict(topology["request"])
    benchmark_request = BenchmarkRequest.from_dict({
        "schema_version": 1,
        "request_id": intent.request_id,
        "objective": intent.objective,
        "topology_id": topology["topology_id"],
        "applications": list(intent.applications),
        "seed": intent.seed,
        "difficulty": intent.difficulty,
        "scale": intent.scale,
        "fault_count": intent.fault_count,
        "fault_types": list(intent.fault_types),
        "observer_template": "network_observer",
        "prepare_topology": False,
        "execute_lifecycle": False,
        "qualification_runs": 2,
        "publish": False,
        "resource_class": _resource_class(intent.scale),
    })
    impact = []
    for index in range(intent.fault_count):
        impact.append({
            "fault_type": intent.fault_types[index % len(intent.fault_types)],
            "application": intent.applications[index % len(intent.applications)],
            "protected_capability": "network_observer" if intent.observer_required else None,
            "maximum_affected_assets": intent.fault_count,
        })
    preview = {
        "schema_version": 1,
        "mode": "plan_only_no_container_launch",
        "topology": {
            "topology_id": topology["topology_id"],
            "topology_fingerprint": topology["topology_fingerprint"],
            "resource_estimate": topology["resource_estimate"],
        },
        "applications": list(intent.applications),
        "fault_impact": impact,
        "fault_relationship": intent.fault_relationship,
        "observer_protected": intent.observer_required,
        "requested_scale": intent.scale,
        "requested_difficulty": intent.difficulty,
        "execution_authorized": False,
        "publication_requested": intent.publish_requested,
        "risks": [
            "LLM output is untrusted until schema, capability and policy checks pass",
            "real Docker execution requires a one-time approval token",
            "publication requires successful formal qualification",
            "1000/10000 scale checks may be plan/performance/sampled rather than full deployment",
        ],
    }
    fingerprint = _sha({
        "intent": intent.fingerprint,
        "catalog": catalog.fingerprint,
        "topology": topology["topology_fingerprint"],
        "benchmark_request": benchmark_request.fingerprint,
    })
    preview["plan_fingerprint"] = fingerprint
    return CompiledNaturalLanguagePlan(
        intent, topology_request, benchmark_request, preview, fingerprint
    )
