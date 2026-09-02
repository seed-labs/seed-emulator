"""Semantic resolver-failure benchmark driver."""

from typing import Any

from benchmark_agent.faults.base import binding, require
from benchmark_agent.models import FaultCapabilityBinding, FaultCapabilityProposal

REQUIRED_PROBES = {"dns.resolver", "dns.query"}


def verify(
    proposal: FaultCapabilityProposal, facts: dict[str, Any], evidence: dict[str, Any]
) -> FaultCapabilityBinding:
    name = proposal.parameters.get("name")
    require(
        isinstance(name, str) and 0 < len(name) <= 253,
        "DNS proposal requires a bounded query name",
    )
    require(
        evidence["operations"].get("dns.resolver", False),
        "resolver state is unavailable",
    )
    return binding(
        proposal,
        facts,
        evidence,
        driver="dns_resolver_failure",
        baseline_probe={"tool": "operation.dns.probe", "arguments": {"name": name}},
        inject_operation={
            "tool": "operation.dns.set_nameserver",
            "arguments": {"nameserver": "192.0.2.1"},
        },
        recovery_operation={
            "tool": "operation.dns.set_nameserver",
            "arguments": {"nameserver": "127.0.0.11"},
        },
        candidate_operations=[
            {"tool": "operation.dns.inspect", "action": "inspect_dns"},
            {
                "tool": "operation.dns.probe",
                "action": "probe_dns",
                "arguments": {"name": name},
            },
            {
                "tool": "operation.dns.set_nameserver",
                "action": "repair_dns",
                "arguments": {"nameserver": "127.0.0.11"},
            },
        ],
    )
