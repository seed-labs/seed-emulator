"""Registry and deterministic proposal verification."""

from collections.abc import Callable
from typing import Any

from benchmark_agent.faults import container, dns, firewall, netem
from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal

Verifier = Callable[
    [FaultCapabilityProposal, dict[str, Any], dict[str, Any]], FaultCapabilityBinding
]

DRIVERS: dict[str, tuple[set[str], Verifier]] = {
    "container_stopped": (container.REQUIRED_PROBES, container.verify),
    "dns_resolver_failure": (dns.REQUIRED_PROBES, dns.verify),
    "firewall_drop": (firewall.REQUIRED_PROBES, firewall.verify),
    "netem_delay": (netem.REQUIRED_PROBES, netem.verify),
}


def verify_proposal(
    proposal: FaultCapabilityProposal, facts: dict[str, Any], evidence: dict[str, Any]
) -> FaultCapabilityBinding:
    required, verifier = DRIVERS[proposal.fault_kind]
    requested = set(proposal.requested_probes)
    if not required.issubset(requested):
        missing = ", ".join(sorted(required - requested))
        raise ValueError(f"proposal omitted required read-only probes: {missing}")
    return verifier(proposal, facts, evidence)


def capability_catalog(bindings: list[FaultCapabilityBinding]) -> dict[str, Any]:
    return {
        "available_faults": sorted({item.fault_kind for item in bindings}),
        "fault_capabilities": [item.model_dump() for item in bindings],
    }


def verify_evidence_drift(
    binding: FaultCapabilityBinding, current: dict[str, Any]
) -> None:
    """Reject loss of an operation capability used during verification."""

    if current.get("service") != binding.target_service:
        raise ValueError("capability evidence target drifted")
    before = binding.evidence_snapshot.get("operations", {})
    after = current.get("operations", {})
    lost = sorted(
        name
        for name, value in before.items()
        if value is True and after.get(name) is not True
    )
    if lost:
        raise ValueError(
            "capability evidence drifted; lost operations: " + ", ".join(lost)
        )
