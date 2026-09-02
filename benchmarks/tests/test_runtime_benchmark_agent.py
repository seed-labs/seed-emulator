"""Deterministic tests for the first benchmark-agent vertical slice."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_agent.faults import verify_proposal
from benchmark_agent.models import BenchmarkPlan, BenchmarkRequest
from benchmark_agent.nl import compile_scenario, validate_proposal
from benchmark_agent.scenario import load_scenario
from benchmark_agent.workflow import build_request, run_runtime_benchmark
from pydantic import ValidationError

_RUNTIME_SUMMARY = {
    "schema_version": 1,
    "mode": "runtime_discovered",
    "topology_id": "existing-lab",
    "name": "existing-lab",
    "project": "existing-lab",
    "services": ["hnode_150_host_0"],
    "probes": [],
    "fingerprint": "c" * 64,
}


class FakeToolService:
    def __init__(self) -> None:
        self.healthy = True
        self.running = True
        self.calls: list[str] = []
        self.tokens: set[str] = set()
        self.sessions: set[str] = set()

    def invoke(self, base_url, name, arguments, timeout=300):
        self.calls.append(name)
        result = {}
        if name == "benchmark.runtime.describe":
            result = {
                "project": arguments["project"],
                "services": [
                    {
                        "service": "client",
                        "name": "host",
                        "status": "running",
                        "image": "seed",
                    },
                    {"service": "hnode_150_host_0", "name": "host-150", "status": "running", "image": "seed"},
                    {"service": "hnode_1_host", "name": "host-1", "status": "running", "image": "seed"},
                ],
            }
        elif name == "benchmark.runtime.service_capabilities":
            result = {
                "project": arguments["project"],
                "service": arguments["service"],
                "operations": {
                    "container.status": True,
                    "container.stop_start": True,
                    "dns.resolver": True,
                },
                "evidence": {},
                "read_only": True,
            }
        elif name in {"benchmark.dns.probe", "operation.dns.probe"}:
            result = {
                "healthy": self.healthy,
                "exit_code": 0 if self.healthy else 2,
                "name": arguments["name"],
            }
        elif name == "operation.dns.set_nameserver":
            self.healthy = arguments["nameserver"] == "127.0.0.11"
            result = {"changed": True, "exit_code": 0}
        elif name == "benchmark.dns.inject":
            self.healthy = False
            token = f"token-{len(self.tokens):032d}"
            self.tokens.add(token)
            result = {"recovery_token": token, "changed": True}
        elif name == "benchmark.dns.recover":
            self.healthy = True
            self.tokens.discard(arguments["recovery_token"])
            result = {"recovered": True}
        elif name in {"benchmark.container.inspect", "operation.container.inspect"}:
            result = {
                "status": "running" if self.running else "exited",
                "running": self.running,
            }
        elif name == "benchmark.container.inject_stop":
            self.running = False
            token = f"token-{len(self.tokens):032d}"
            self.tokens.add(token)
            result = {"recovery_token": token, "stopped": True}
        elif name == "operation.container.stop":
            self.running = False
            result = {"running": False, "status": "exited"}
        elif name == "benchmark.container.recover":
            self.running = True
            self.tokens.discard(arguments["recovery_token"])
            result = {"recovered": True}
        elif name == "operation.container.start":
            self.running = True
            result = {"running": True, "status": "running"}
        elif name == "benchmark.topology.lifecycle":
            result = {
                "action": arguments["action"],
                "successful": True,
                "exit_code": 0,
            }
        else:
            raise AssertionError(name)
        return {
            "tool": name,
            "arguments": arguments,
            "result": result,
            "duration_ms": 1.0,
        }


class RuntimeBenchmarkAgentTests(unittest.TestCase):
    def test_request_and_plan_reject_unknown_fields(self) -> None:
        request = build_request(
            load_scenario(
                Path(__file__).with_name("fixtures") / "runtime_scenario.json"
            )
        )
        self.assertIsInstance(request, BenchmarkRequest)
        self.assertEqual(request.fault["kind"], "dns_resolver_failure")
        self.assertEqual(request.fault["target_service"], "client")
        with self.assertRaises(ValidationError):
            BenchmarkPlan.model_validate(
                {
                    "schema_version": 1,
                    "state": "approved",
                    "request": {},
                    "runtime": {},
                    "lifecycle": [],
                    "fingerprint": "x",
                    "unexpected": True,
                }
            )

    def test_api_only_lifecycle_builds_bundle_and_scores_candidate(self) -> None:
        tools = FakeToolService()

        def fake_runner(*, agent_view, max_calls):
            tools.healthy = True  # simulated Adapter repair effect
            return (
                [
                    {
                        "turn": 0,
                        "action": "inspect_dns",
                        "reasoning": "Inspect resolver state.",
                        "observation": {
                            "content": "nameserver 192.0.2.1\n",
                            "exit_code": 0,
                        },
                    },
                    {
                        "turn": 1,
                        "action": "repair_dns",
                        "reasoning": "Restore the platform resolver.",
                        "observation": {"repaired": True},
                    },
                ],
                {"name": "fake"},
            )

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "benchmark_agent.workflow.wait_for_service",
                    return_value={"status": "ok"},
                ),
                patch("benchmark_agent.workflow.invoke_tool", side_effect=tools.invoke),
            ):
                output = run_runtime_benchmark(
                    api_url="http://tool-service",
                    output_root=Path(directory),
                    materialize=False,
                    evaluation_runner=fake_runner,
                    scenario=load_scenario(
                        Path(__file__).with_name("fixtures") / "runtime_scenario.json"
                    ),
                )

            bundle = json.loads((output / "bundle.json").read_text())
            evaluation = json.loads((output / "evaluation.json").read_text())
            cleanup = json.loads((output / "cleanup.json").read_text())
            events = json.loads((output / "events.json").read_text())
            journal_lines = (output / "journal.jsonl").read_text().splitlines()

            self.assertTrue(bundle["qualification"]["passed"])
            self.assertEqual(bundle["capability_grant"]["target_service"], "client")
            self.assertEqual(
                bundle["capability_grant"]["allowed_actions"],
                ["inspect_dns", "probe_dns", "repair_dns", "finish"],
            )
            grant_spec = json.loads((output / "grant_spec.json").read_text())
            self.assertEqual(grant_spec["terminal_action"], "finish")
            self.assertEqual(
                set(grant_spec["actions"]),
                {"inspect_dns", "probe_dns", "repair_dns", "finish"},
            )
            self.assertEqual(bundle["capability_grant"]["enforced_by"], "candidate_adapter")
            self.assertTrue(evaluation["score_report"]["passed"])
            self.assertEqual(evaluation["score_report"]["total"], 100)
            self.assertEqual(evaluation["score_report"]["authorization"], 20)
            self.assertTrue(cleanup["fault_recovered"])
            self.assertEqual(
                json.loads((output / "scenario.json").read_text())["id"],
                "runtime_dns_test",
            )
            self.assertEqual(len(journal_lines), len(events))
            for event in events:
                self.assertFalse(event["ai_invoked"])
            self.assertIn("benchmark.runtime.describe", tools.calls)
            self.assertNotIn("docker", " ".join(tools.calls).lower())

    def test_runtime_discovered_lifecycle_never_materializes(self) -> None:
        tools = FakeToolService()
        proposal = validate_proposal(
            {
                "fault_kind": "container_stopped",
                "target_service": "hnode_150_host_0",
                "requested_probes": ["container.status"],
                "parameters": {},
                "reason": "Stop the discovered service.",
                "confidence": 0.5,
            },
            _RUNTIME_SUMMARY,
        )
        evidence = {
            "service": "hnode_150_host_0",
            "operations": {"container.stop_start": True},
            "evidence": {},
        }
        binding = verify_proposal(proposal, _RUNTIME_SUMMARY, evidence)
        scenario = compile_scenario(
            proposal, binding, _RUNTIME_SUMMARY, text="stop the host"
        )

        def fake_runner(*, agent_view, max_calls):
            tools.running = True  # simulated Adapter repair effect
            return (
                [
                    {
                        "turn": 0,
                        "action": "start_service",
                        "reasoning": "Restore the stopped service.",
                        "observation": {"running": True, "status": "running"},
                    }
                ],
                {"name": "fake"},
            )

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "benchmark_agent.workflow.wait_for_service",
                    return_value={"status": "ok"},
                ),
                patch("benchmark_agent.workflow.invoke_tool", side_effect=tools.invoke),
            ):
                output = run_runtime_benchmark(
                    api_url="http://tool-service",
                    output_root=Path(directory),
                    evaluation_runner=fake_runner,
                    scenario=scenario,
                )

            request = json.loads((output / "request.json").read_text())
            evaluation = json.loads((output / "evaluation.json").read_text())
            cleanup = json.loads((output / "cleanup.json").read_text())

        self.assertEqual(request["topology_source"]["mode"], "runtime_discovered")
        self.assertEqual(request["topology_source"]["compose_project"], "existing-lab")
        self.assertNotIn("benchmark.topology.lifecycle", tools.calls)
        self.assertIn("benchmark.runtime.describe", tools.calls)
        self.assertTrue(evaluation["score_report"]["passed"])
        self.assertEqual(evaluation["score_report"]["total"], 100)
        self.assertTrue(cleanup["fault_recovered"])
        # The benchmark does not own a runtime-discovered topology: it must stay up.
        self.assertFalse(cleanup["topology_down"])

    def test_python_discovered_artifact_runs_through_tool_service_lifecycle(
        self,
    ) -> None:
        tools = FakeToolService()
        summary = {
            "schema_version": 1,
            "mode": "python_discovered",
            "topology_id": "custom",
            "name": "custom",
            "project": "discover-custom",
            "source": {
                "script_path": "/trusted/custom.py",
                "artifact_id": "discover-custom",
                "compose_path": "/artifacts/discover-custom/compiled/docker-compose.yml",
            },
            "fingerprint": "b" * 64,
            "services": ["hnode_1_host"],
            "probes": [],
        }
        proposal = validate_proposal(
            {
                "fault_kind": "container_stopped",
                "target_service": "hnode_1_host",
                "requested_probes": ["container.status"],
                "parameters": {},
                "reason": "Stop the inferred host.",
                "topology_purpose": "custom network lab",
                "target_role": "host",
                "confidence": 0.6,
            },
            summary,
        )
        evidence = {
            "service": "hnode_1_host",
            "operations": {"container.stop_start": True},
            "evidence": {},
        }
        binding = verify_proposal(proposal, summary, evidence)
        scenario = compile_scenario(proposal, binding, summary, text="stop the host")

        def fake_runner(*, agent_view, max_calls):
            tools.running = True
            return (
                [{"action": "start_service", "observation": {"running": True}}],
                {"name": "fake"},
            )

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "benchmark_agent.workflow.wait_for_service",
                    return_value={"status": "ok"},
                ),
                patch("benchmark_agent.workflow.invoke_tool", side_effect=tools.invoke),
            ):
                output = run_runtime_benchmark(
                    api_url="http://tool-service",
                    output_root=Path(directory),
                    evaluation_runner=fake_runner,
                    scenario=scenario,
                )
            cleanup = json.loads((output / "cleanup.json").read_text())

        lifecycle_calls = [
            name for name in tools.calls if name == "benchmark.topology.lifecycle"
        ]
        self.assertGreaterEqual(len(lifecycle_calls), 4)
        self.assertTrue(cleanup["topology_down"])


if __name__ == "__main__":
    unittest.main()
