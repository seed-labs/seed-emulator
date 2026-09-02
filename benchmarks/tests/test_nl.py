"""Tests for the constrained natural-language planning bridge."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_agent.faults import verify_proposal
from benchmark_agent.nl import (
    compile_scenario,
    plan_runtime_natural_language,
    summarize_python_topology,
    summarize_runtime_topology,
    validate_proposal,
)


class RuntimeDiscoveryTests(unittest.TestCase):
    def _inventory_receipt(self, project: str, containers: list[dict]) -> dict:
        return {
            "tool": "benchmark.runtime.describe",
            "arguments": {"project": project},
            "result": {
                "project": project,
                "services": containers,
                "networks": [{"name": "lab-net"}],
            },
            "duration_ms": 1.0,
        }

    def test_runtime_summary_discovers_running_services(self) -> None:
        receipt = self._inventory_receipt(
            "lab",
            [
                {
                    "service": "web",
                    "name": "lab-web-1",
                    "status": "running",
                    "image": "x",
                },
                {"service": "db", "name": "lab-db-1", "status": "exited", "image": "x"},
            ],
        )
        with patch("benchmark_agent.nl.invoke_tool", return_value=receipt):
            summary = summarize_runtime_topology("http://tool-service", "lab")
        self.assertEqual(summary["mode"], "runtime_discovered")
        self.assertEqual(summary["project"], "lab")
        self.assertEqual(summary["services"], ["web"])
        self.assertEqual(summary["probes"], [])
        self.assertNotIn("available_faults", summary)
        self.assertEqual(summary["networks"], [{"name": "lab-net"}])
        self.assertEqual(summary["default_probes"][0]["type"], "service_running")

    def test_python_summary_is_received_only_through_tool_service(self) -> None:
        descriptor = {
            "schema_version": 1,
            "mode": "python_discovered",
            "topology_id": "A00",
            "name": "simple_as",
            "project": "discover-case",
            "source": {
                "seed_root": "/seed",
                "script_path": "examples/basic/A00/simple_as.py",
                "compose_path": "/artifacts/discover-case/compiled/docker-compose.yml",
                "artifact_id": "discover-case",
            },
            "services": [
                {"service": "hnode_150_host", "image": "seed", "networks": ["net0"]}
            ],
            "networks": [{"name": "net0"}],
            "default_probes": [
                {"type": "service_running", "service": "hnode_150_host"}
            ],
            "limits": {"service_count": 1, "max_services": 500},
            "fingerprint": "a" * 64,
        }
        receipt = {"result": {"successful": True, "descriptor": descriptor}}
        with patch("benchmark_agent.nl.invoke_tool", return_value=receipt) as invoke:
            summary = summarize_python_topology(
                "http://tool-service",
                Path("examples/basic/A00/simple_as.py"),
                seed_root=Path("/seed"),
                artifact_id="discover-case",
            )
        self.assertEqual(summary["services"], ["hnode_150_host"])
        self.assertEqual(summary["mode"], "python_discovered")
        self.assertEqual(invoke.call_args.args[1], "benchmark.topology.discover_python")
        proposal = validate_proposal(
            {
                "fault_kind": "container_stopped",
                "target_service": "hnode_150_host",
                "requested_probes": ["container.status"],
                "parameters": {},
                "reason": "Stop the inferred host.",
                "topology_purpose": "small routed lab",
                "target_role": "host",
                "confidence": 0.65,
            },
            summary,
        )
        evidence = {
            "service": "hnode_150_host",
            "operations": {"container.stop_start": True},
            "evidence": {},
        }
        binding = verify_proposal(proposal, summary, evidence)
        scenario = compile_scenario(proposal, binding, summary, text="stop one host")
        self.assertEqual(scenario.topology.artifact_id, "discover-case")
        self.assertTrue(scenario.topology.compose_path.endswith("docker-compose.yml"))
        self.assertEqual(scenario.topology.interpretation["target_role"], "host")

    def test_runtime_summary_rejects_project_without_running_services(self) -> None:
        receipt = self._inventory_receipt(
            "lab",
            [{"service": "web", "name": "lab-web-1", "status": "exited", "image": "x"}],
        )
        with (
            patch("benchmark_agent.nl.invoke_tool", return_value=receipt),
            self.assertRaisesRegex(ValueError, "no running services"),
        ):
            summarize_runtime_topology("http://tool-service", "lab")

    def test_runtime_intent_compiles_runtime_scenario(self) -> None:
        summary = {
            "schema_version": 1,
            "mode": "runtime_discovered",
            "topology_id": "lab",
            "name": "lab",
            "project": "lab",
            "services": ["web"],
            "probes": [],
            "fingerprint": "b" * 64,
        }
        raw = {
            "fault_kind": "container_stopped",
            "target_service": "web",
            "requested_probes": ["container.status"],
            "parameters": {},
            "reason": "Stop the discovered service.",
            "confidence": 0.5,
        }
        proposal = validate_proposal(raw, summary)
        evidence = {
            "service": "web",
            "operations": {"container.stop_start": True},
            "evidence": {},
        }
        binding = verify_proposal(proposal, summary, evidence)
        scenario = compile_scenario(
            proposal, binding, summary, text="stop the web service"
        )
        self.assertEqual(scenario.topology.mode, "runtime_discovered")
        self.assertEqual(scenario.topology.project, "lab")
        self.assertEqual(scenario.project, "lab")

    def test_runtime_plan_persists_audit_and_does_not_execute(self) -> None:
        def provider(text, summary):
            return (
                {
                    "fault_kind": "container_stopped",
                    "target_service": "web",
                    "requested_probes": ["container.status"],
                    "parameters": {},
                    "reason": "Stop the discovered service.",
                    "confidence": 0.5,
                },
                {"provider": "fake", "structured_output": True},
            )

        receipt = self._inventory_receipt(
            "lab",
            [
                {
                    "service": "web",
                    "name": "lab-web-1",
                    "status": "running",
                    "image": "x",
                }
            ],
        )
        capability_receipt = {
            "result": {
                "project": "lab",
                "service": "web",
                "operations": {"container.stop_start": True},
                "evidence": {},
                "read_only": True,
            }
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "benchmark_agent.nl.invoke_tool",
                side_effect=[receipt, capability_receipt],
            ),
        ):
            output = plan_runtime_natural_language(
                text="stop web",
                project="lab",
                api_url="http://tool-service",
                output_root=Path(directory),
                provider=provider,
            )
            request = json.loads((output / "request.json").read_text())
            scenario = json.loads((output / "scenario.json").read_text())
            risk = json.loads((output / "risk_report.json").read_text())
            catalog = json.loads((output / "capability_catalog.json").read_text())
        self.assertEqual(request["mode"], "runtime_discovered")
        self.assertEqual(request["project"], "lab")
        self.assertEqual(scenario["topology"]["mode"], "runtime_discovered")
        self.assertEqual(scenario["topology"]["project"], "lab")
        self.assertNotIn("source_path", scenario["topology"])
        self.assertEqual(risk["topology_boundary"], "lab")
        self.assertTrue(risk["plan_only"])
        self.assertFalse(risk["docker_changed"])
        self.assertEqual(catalog["available_faults"], ["container_stopped"])


if __name__ == "__main__":
    unittest.main()
