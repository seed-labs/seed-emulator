"""Tests for the Adapter grant spec and local policy layer."""

import tempfile
import unittest
from pathlib import Path

from benchmark_adapter.grants import (
    GrantSpecError,
    check_action,
    validate_grant_spec,
)
from benchmark_adapter.trace import TraceRecorder


def _spec(**overrides):
    spec = {
        "agent_view": {"objective": "fix dns"},
        "allowed_actions": ["inspect_dns", "probe_dns", "repair_dns", "finish"],
        "actions": {
            "inspect_dns": {
                "tool": "benchmark.dns.inspect",
                "fields": ["content"],
                "arguments": {},
            },
            "probe_dns": {
                "tool": "benchmark.dns.probe",
                "fields": ["healthy"],
                "arguments": {"name": "host"},
            },
            "repair_dns": {
                "tool": "benchmark.dns.repair",
                "fields": ["repaired"],
                "arguments": {"nameserver": "127.0.0.11"},
            },
            "finish": {"tool": None, "terminal": True, "fields": []},
        },
        "terminal_action": "finish",
        "target_service": "svc",
        "project": "proj",
        "max_calls": 3,
        "benchmark_id": "b1",
        "tool_service_url": "http://127.0.0.1:8000",
        "grant_token": "t" * 32,
        "trace_path": str(Path(tempfile.gettempdir()) / "trace.jsonl"),
    }
    spec.update(overrides)
    return spec


class GrantSpecTests(unittest.TestCase):
    def test_missing_keys_rejected(self) -> None:
        spec = _spec()
        del spec["tool_service_url"]
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(spec)

    def test_allowed_actions_must_match_declared(self) -> None:
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(_spec(allowed_actions=["probe_dns"]))

    def test_terminal_action_must_be_declared_and_terminal(self) -> None:
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(_spec(terminal_action="probe_dns"))
        spec = _spec()
        spec["actions"]["finish"]["terminal"] = False
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(spec)

    def test_non_terminal_action_requires_tool(self) -> None:
        spec = _spec()
        spec["actions"]["repair_dns"]["tool"] = None
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(spec)

    def test_terminal_action_must_not_declare_tool(self) -> None:
        spec = _spec()
        spec["actions"]["finish"]["tool"] = "benchmark.dns.probe"
        with self.assertRaises(GrantSpecError):
            validate_grant_spec(spec)

    def test_check_action_policy(self) -> None:
        spec = _spec()
        self.assertIsNone(check_action(spec, "probe_dns", 0))
        self.assertEqual(check_action(spec, "bogus", 0), "unknown action: bogus")
        self.assertEqual(
            check_action(
                _spec(allowed_actions=["probe_dns", "finish"]), "repair_dns", 0
            ),
            "action not granted: repair_dns",
        )
        self.assertEqual(
            check_action(spec, "probe_dns", 3), "grant call budget exhausted"
        )

    def test_trace_recorder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            recorder = TraceRecorder(path)
            recorder.append({"action": "probe_dns"})
            recorder.append({"action": "finish"})
            self.assertEqual(len(recorder.entries()), 2)
            self.assertEqual(len(path.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
