"""Semantic firewall-drop benchmark driver."""

from typing import Any

from benchmark_agent.faults.base import binding, require
from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal

REQUIRED_PROBES = {"firewall.backend", "network.reachability"}


def verify(
    proposal: FaultCapabilityProposal, facts: dict[str, Any], evidence: dict[str, Any]
) -> FaultCapabilityBinding:
    destination = proposal.parameters.get("destination")
    require(
        isinstance(destination, str) and bool(destination),
        "firewall proposal requires destination",
    )
    require(
        evidence["operations"].get("firewall.iptables", False),
        "iptables operation is unavailable",
    )
    return binding(
        proposal,
        facts,
        evidence,
        driver="firewall_drop",
        baseline_probe={
            "tool": "operation.network.probe",
            "arguments": {"destination": destination},
        },
        inject_operation={
            "tool": "operation.firewall.add_drop",
            "arguments": {"destination": destination},
        },
        recovery_operation={
            "tool": "operation.firewall.delete_drop",
            "arguments": {"destination": destination},
        },
        candidate_operations=[
            {
                "tool": "operation.firewall.inspect_drop",
                "action": "inspect_firewall",
                "arguments": {"destination": destination},
            },
            {
                "tool": "operation.network.probe",
                "action": "probe_network",
                "arguments": {"destination": destination},
            },
            {
                "tool": "operation.firewall.delete_drop",
                "action": "repair_firewall",
                "arguments": {"destination": destination},
            },
        ],
    )
