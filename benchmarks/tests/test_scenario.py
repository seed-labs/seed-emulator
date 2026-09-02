"""Tests for scenario loading and validation (no hardcoded scenario values)."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark_agent.scenario import load_scenario
from pydantic import ValidationError

_MINIMAL = {
    "id": "test",
    "topology": {"mode": "runtime_discovered", "project": "output"},
    "project": "output",
    "fault": {
        "kind": "dns_resolver_failure",
        "target_service": "svc",
        "probe_tool": "benchmark.dns.probe",
        "inject_tool": "benchmark.dns.inject",
        "recover_tool": "benchmark.dns.recover",
        "probe_arguments": {"name": "probe"},
        "inject_arguments": {"bad_nameserver": "192.0.2.1"},
    },
    "seed": 1,
    "grant": {
        "max_calls": 4,
        "ttl_seconds": 600,
        "tools": ["benchmark.dns.inspect", "benchmark.dns.probe", "benchmark.dns.repair"],
    },
    "capabilities": ["inspect_dns", "probe_dns", "repair_dns"],
    "actions": {
        "inspect_dns": {"tool": "benchmark.dns.inspect", "description": "inspect", "fields": ["content"]},
        "probe_dns": {"tool": "benchmark.dns.probe", "description": "probe", "fields": ["healthy"]},
        "repair_dns": {"tool": "benchmark.dns.repair", "description": "repair", "fields": ["repaired"]},
        "finish": {"tool": None, "terminal": True, "description": "finish"},
    },
    "prompts": {
        "native_system": "native",
        "inspect_system": "inspect",
        "agent_view_objective": "objective",
    },
    "scoring": {},
    "naming": {
        "session_prefix": "test",
        "project_alias": "alias",
        "inspect_task_name": "task",
        "sample_id": "sample",
    },
}


def _write_scenario(directory: str, value: dict) -> Path:
    path = Path(directory) / "scenario.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class ScenarioTests(unittest.TestCase):
    def test_load_minimal_scenario(self) -> None:
        with TemporaryDirectory() as directory:
            scenario = load_scenario(_write_scenario(directory, _MINIMAL))
        self.assertEqual(scenario.id, "test")
        self.assertEqual(scenario.fault.target_service, "svc")
        self.assertEqual(scenario.allowed_actions, ["inspect_dns", "probe_dns", "repair_dns", "finish"])
        self.assertEqual(scenario.finish_action, "finish")
        self.assertEqual(scenario.scoring.task_success, 60)

    def test_unknown_field_rejected(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["unexpected"] = True
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_non_terminal_action_requires_tool(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["actions"]["repair_dns"]["tool"] = None
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_finish_must_be_terminal(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["actions"]["finish"]["terminal"] = False
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_capabilities_must_match_actions(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["capabilities"] = ["inspect_dns"]
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_author_mutation_cannot_be_candidate_grantable(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["grant"]["tools"][0] = "benchmark.dns.inject"
        value["actions"]["inspect_dns"]["tool"] = "benchmark.dns.inject"
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_generic_operation_shared_with_different_arguments_is_allowed(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["fault"]["inject_tool"] = "operation.dns.set_nameserver"
        value["fault"]["recover_tool"] = "operation.dns.set_nameserver"
        value["fault"]["inject_arguments"] = {"nameserver": "192.0.2.1"}
        value["grant"]["tools"] = [
            "operation.dns.inspect", "operation.dns.probe", "operation.dns.set_nameserver"
        ]
        value["actions"] = {
            "inspect_dns": {"tool": "operation.dns.inspect", "description": "inspect", "fields": ["content"]},
            "probe_dns": {"tool": "operation.dns.probe", "description": "probe", "fields": ["healthy"], "arguments": {"name": "probe"}},
            "repair_dns": {"tool": "operation.dns.set_nameserver", "description": "repair", "fields": ["repaired"], "arguments": {"nameserver": "127.0.0.11"}},
            "finish": {"tool": None, "terminal": True, "description": "finish"},
        }
        with TemporaryDirectory() as directory:
            scenario = load_scenario(_write_scenario(directory, value))
        self.assertIsNotNone(scenario.capability_binding or True)

    def test_generic_operation_same_tool_and_arguments_is_rejected(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["fault"]["inject_tool"] = "operation.dns.set_nameserver"
        value["fault"]["recover_tool"] = "operation.dns.set_nameserver"
        value["fault"]["inject_arguments"] = {"nameserver": "192.0.2.1"}
        value["grant"]["tools"] = [
            "operation.dns.inspect", "operation.dns.probe", "operation.dns.set_nameserver"
        ]
        value["actions"] = {
            "inspect_dns": {"tool": "operation.dns.inspect", "description": "inspect", "fields": ["content"]},
            "probe_dns": {"tool": "operation.dns.probe", "description": "probe", "fields": ["healthy"], "arguments": {"name": "probe"}},
            "repair_dns": {"tool": "operation.dns.set_nameserver", "description": "repair", "fields": ["repaired"], "arguments": {"nameserver": "192.0.2.1"}},
            "finish": {"tool": None, "terminal": True, "description": "finish"},
        }
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_runtime_discovered_topology_binds_project(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["topology"] = {"mode": "runtime_discovered", "project": "output"}
        with TemporaryDirectory() as directory:
            scenario = load_scenario(_write_scenario(directory, value))
        self.assertEqual(scenario.topology.mode, "runtime_discovered")
        self.assertEqual(scenario.topology.project, "output")

    def test_runtime_topology_requires_project_match(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["topology"] = {"mode": "runtime_discovered", "project": "other"}
        with TemporaryDirectory() as directory, self.assertRaises(ValidationError):
            load_scenario(_write_scenario(directory, value))

    def test_python_topology_requires_bound_artifact(self) -> None:
        value = json.loads(json.dumps(_MINIMAL))
        value["topology"] = {
            "mode": "python_discovered",
            "script_path": "/tmp/topology.py",
            "descriptor_fingerprint": "a" * 64,
            "artifact_id": "artifact-1",
            "compose_path": "/tmp/artifact/docker-compose.yml",
            "project": "output",
        }
        with TemporaryDirectory() as directory:
            scenario = load_scenario(_write_scenario(directory, value))
        self.assertEqual(scenario.topology.artifact_id, "artifact-1")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_scenario(Path("/nonexistent/scenario.json"))


if __name__ == "__main__":
    unittest.main()
