"""Compatibility adapters from existing benchmark templates to FaultSpec v1."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.faults.compiler import compile_fault_set
from generator.faults.models import CompiledFaultPlan, FaultSpec


def _asset(container: str, parameters: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "container": container,
        "asn": int(parameters.get("source_asn", parameters.get("correct_asn", 0))),
        "role": "BorderRouter" if "router" in container else "Host",
        "interfaces": [{"name": str(parameters.get("source_interface", "lan0"))}],
    }


def _spec(
    fault_id: str,
    fault_type: str,
    container: str,
    parameters: Mapping[str, Any],
    *,
    seed: str,
) -> FaultSpec:
    return FaultSpec(
        fault_id=fault_id, fault_type=fault_type,
        selector={"container": container}, parameters=dict(parameters),
        expectations={"must_break": [fault_id], "must_preserve": []},
        safety={"max_affected_assets": 2, "max_affected_asns": 2,
                "protected_assets": [], "require_recovery": True},
        seed=seed, schedule={"at_seconds": 0, "duration_seconds": 0},
    )


def compile_template_faults(
    template_id: str,
    parameters: Mapping[str, Any],
    *,
    topology_fingerprint: str = "legacy-audited-topology",
) -> CompiledFaultPlan:
    """Compile migrated network primitives while preserving their semantics."""
    p = dict(parameters)
    specs = []
    if template_id == "container_stopped":
        specs.append(_spec("container_stopped", "container.stopped", str(p["container"]), p, seed="0"))
    elif template_id == "dns_nameserver":
        specs.append(_spec("dns_nameserver", "dns.nameserver", str(p["container"]), p, seed="0"))
    elif template_id == "bird_wrong_asn":
        specs.append(_spec("bird_wrong_asn", "routing.bird.wrong_asn", str(p["container"]), p, seed="0"))
    elif template_id == "random_complex_transit_acl":
        specs.append(_spec("random_transit_acl", "network.acl.scoped", str(p["source_router"]), p, seed="0"))
    elif template_id == "random_complex_dual_bgp_acl":
        router = str(p["source_router"])
        specs.extend((
            _spec("random_bird_wrong_asn", "routing.bird.wrong_asn", router, p, seed="0"),
            _spec("random_transit_acl", "network.acl.scoped", router, p, seed="0"),
        ))
    elif template_id == "netem_impairment":
        specs.append(_spec("netem_impairment", "network.netem", str(p["container"]), p, seed="0"))
    else:
        raise ValueError(f"template is not migrated to FaultSpec v1: {template_id}")
    containers = {str(item.selector["container"]) for item in specs}
    capabilities = {
        "topology_fingerprint": topology_fingerprint,
        "assets": [_asset(container, p) for container in sorted(containers)],
    }
    return compile_fault_set(
        tuple(specs), capabilities,
        relationship="single" if len(specs) == 1 else "independent",
    )


def rendered_components(plan: CompiledFaultPlan):
    """Adapt a generic compiled plan to the legacy scenario component API."""
    from generator.templates import RenderedFaultComponent

    return tuple(
        RenderedFaultComponent(
            component_id=action.action_id,
            category=action.category,
            target_containers=action.targets,
            artifact=action.artifact,
            faulty_value=action.faulty_value,
            expected_value=action.expected_value,
            inject_order=action.inject_order,
            cleanup_order=action.cleanup_order,
            inject_command=action.inject_command,
            fault_check_command=action.active_check_command,
            fault_verifier_kind=action.active_verifier_kind,
            fault_verifier_value=action.active_verifier_value,
            cleanup_command=action.cleanup_command,
            depends_on=action.depends_on,
        )
        for action in plan.actions
    )
