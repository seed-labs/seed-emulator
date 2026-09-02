"""Semantic netem-delay benchmark driver."""

from typing import Any

from benchmark_agent.faults.base import binding, require
from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal

REQUIRED_PROBES = {"network.interfaces", "network.reachability", "netem.qdisc"}


def verify(
    proposal: FaultCapabilityProposal, facts: dict[str, Any], evidence: dict[str, Any]
) -> FaultCapabilityBinding:
    interface = proposal.parameters.get("interface", "eth0")
    destination = proposal.parameters.get("destination")
    delay_ms = proposal.parameters.get("delay_ms")
    jitter_ms = proposal.parameters.get("jitter_ms", 0)
    require(
        isinstance(destination, str) and bool(destination),
        "netem proposal requires destination",
    )
    require(
        isinstance(delay_ms, int) and 1 <= delay_ms <= 2000,
        "netem delay is outside benchmark bounds",
    )
    require(
        isinstance(jitter_ms, int) and 0 <= jitter_ms <= 500,
        "netem jitter is outside benchmark bounds",
    )
    require(
        evidence["operations"].get("netem.tc", False), "tc operation is unavailable"
    )
    require(
        evidence["operations"].get("network.interfaces", False),
        "network interfaces are unavailable",
    )
    return binding(
        proposal,
        facts,
        evidence,
        driver="netem_delay",
        baseline_probe={
            "tool": "operation.network.probe",
            "arguments": {"destination": destination},
        },
        inject_operation={
            "tool": "operation.netem.apply",
            "arguments": {
                "interface": interface,
                "delay_ms": delay_ms,
                "jitter_ms": jitter_ms,
                "loss_percent": 0,
            },
        },
        recovery_operation={
            "tool": "operation.netem.apply",
            "arguments": {
                "interface": interface,
                "delay_ms": 0,
                "jitter_ms": 0,
                "loss_percent": 0,
            },
        },
        candidate_operations=[
            {
                "tool": "operation.netem.inspect",
                "action": "inspect_netem",
                "arguments": {"interface": interface},
            },
            {
                "tool": "operation.network.probe",
                "action": "probe_network",
                "arguments": {"destination": destination},
            },
            {
                "tool": "operation.netem.apply",
                "action": "repair_netem",
                "arguments": {
                    "interface": interface,
                    "delay_ms": 0,
                    "jitter_ms": 0,
                    "loss_percent": 0,
                },
            },
        ],
    )
