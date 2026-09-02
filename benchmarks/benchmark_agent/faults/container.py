"""Semantic stopped-container benchmark driver."""

from typing import Any

from benchmark_agent.faults.base import binding, require
from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal

REQUIRED_PROBES = {"container.status"}


def verify(
    proposal: FaultCapabilityProposal, facts: dict[str, Any], evidence: dict[str, Any]
) -> FaultCapabilityBinding:
    require(
        evidence["operations"].get("container.stop_start", False),
        "container stop/start is unavailable",
    )
    return binding(
        proposal,
        facts,
        evidence,
        driver="container_stopped",
        baseline_probe={"tool": "operation.container.inspect", "arguments": {}},
        inject_operation={"tool": "operation.container.stop", "arguments": {}},
        recovery_operation={"tool": "operation.container.start", "arguments": {}},
        candidate_operations=[
            {"tool": "operation.container.inspect", "action": "inspect_service"},
            {"tool": "operation.container.start", "action": "start_service"},
        ],
    )
