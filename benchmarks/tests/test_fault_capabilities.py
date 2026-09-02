"""Deterministic tests for benchmark-owned semantic fault capabilities."""

import unittest

from benchmark_agent.faults import (
    capability_catalog,
    verify_evidence_drift,
    verify_proposal,
)
from benchmark_agent.models import FaultCapabilityProposal

_FACTS = {"fingerprint": "f" * 64}


def _proposal(
    kind: str, probes: list[str], parameters: dict
) -> FaultCapabilityProposal:
    return FaultCapabilityProposal.model_validate(
        {
            "fault_kind": kind,
            "target_service": "node",
            "requested_probes": probes,
            "parameters": parameters,
            "reason": "meaningful test",
            "confidence": 0.7,
        }
    )


class FaultCapabilityTests(unittest.TestCase):
    def test_all_four_semantic_drivers_verify(self) -> None:
        evidence = {
            "service": "node",
            "operations": {
                "container.stop_start": True,
                "dns.resolver": True,
                "firewall.iptables": True,
                "netem.tc": True,
                "network.interfaces": True,
            },
            "evidence": {},
        }
        proposals = [
            _proposal("container_stopped", ["container.status"], {}),
            _proposal(
                "dns_resolver_failure",
                ["dns.resolver", "dns.query"],
                {"name": "example.test"},
            ),
            _proposal(
                "firewall_drop",
                ["firewall.backend", "network.reachability"],
                {"destination": "10.0.0.1"},
            ),
            _proposal(
                "netem_delay",
                ["network.interfaces", "network.reachability", "netem.qdisc"],
                {
                    "destination": "10.0.0.1",
                    "interface": "eth0",
                    "delay_ms": 100,
                    "jitter_ms": 10,
                },
            ),
        ]
        bindings = [verify_proposal(item, _FACTS, evidence) for item in proposals]
        catalog = capability_catalog(bindings)
        self.assertEqual(len(catalog["fault_capabilities"]), 4)
        self.assertEqual(
            set(catalog["available_faults"]), {item.fault_kind for item in proposals}
        )

    def test_missing_required_probe_is_rejected(self) -> None:
        proposal = _proposal(
            "dns_resolver_failure", ["dns.resolver"], {"name": "example.test"}
        )
        with self.assertRaisesRegex(ValueError, "omitted required"):
            verify_proposal(
                proposal,
                _FACTS,
                {"service": "node", "operations": {"dns.resolver": True}},
            )

    def test_lost_operation_is_evidence_drift(self) -> None:
        proposal = _proposal("container_stopped", ["container.status"], {})
        binding = verify_proposal(
            proposal,
            _FACTS,
            {
                "service": "node",
                "operations": {"container.stop_start": True},
                "evidence": {},
            },
        )
        with self.assertRaisesRegex(ValueError, "drifted"):
            verify_evidence_drift(
                binding,
                {"service": "node", "operations": {"container.stop_start": False}},
            )


if __name__ == "__main__":
    unittest.main()
