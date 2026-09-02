"""Tests for the optional Inspect AI candidate harness."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from benchmark_agent.inspect_runner import (
    inspect_available,
    run_inspect_candidate_evaluation,
)
from benchmark_agent.scenario import load_scenario

_SCENARIO = Path(__file__).with_name("fixtures") / "runtime_scenario.json"


class InspectRunnerTests(unittest.TestCase):
    def test_dependency_probe_is_boolean(self) -> None:
        self.assertIsInstance(inspect_available(), bool)

    def test_dependency_probe_handles_missing_package(self) -> None:
        real_import = __import__

        def importing(name, *args, **kwargs):
            if name == "inspect_ai":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=importing):
            self.assertFalse(inspect_available())

    @unittest.skipUnless(inspect_available(), "optional Inspect dependency is absent")
    def test_real_inspect_loop_uses_only_adapter_actions(self) -> None:
        from inspect_ai.model import ModelOutput, get_model

        outputs = [
            ModelOutput.for_tool_call("mock", "inspect_dns", {"reasoning": "inspect"}),
            ModelOutput.for_tool_call("mock", "probe_dns", {"reasoning": "confirm"}),
            ModelOutput.for_tool_call("mock", "repair_dns", {"reasoning": "repair"}),
            ModelOutput.for_tool_call("mock", "probe_dns", {"reasoning": "verify"}),
            ModelOutput.for_tool_call("mock", "finish", {"reasoning": "healthy"}),
            ModelOutput.from_content("mock", "completed"),
        ]
        model = get_model("mockllm/model", custom_outputs=outputs, memoize=False)
        observations = [
            {"nameserver": "192.0.2.1"},
            {"healthy": False},
            {"repaired": True},
            {"healthy": True},
        ]
        with TemporaryDirectory() as directory, patch(
            "benchmark_agent.inspect_runner.post_action",
            side_effect=observations,
        ) as adapter:
            trace, metadata = run_inspect_candidate_evaluation(
                adapter_url="http://adapter.invalid",
                agent_view={"objective": "repair DNS", "service": "node"},
                log_dir=Path(directory),
                scenario=load_scenario(_SCENARIO),
                model=model,
                max_calls=6,
            )
        self.assertEqual(
            [item["action"] for item in trace],
            ["inspect_dns", "probe_dns", "repair_dns", "probe_dns", "finish"],
        )
        self.assertEqual(adapter.call_count, 4)
        self.assertEqual(metadata["name"], "inspect-ai")
        self.assertEqual(metadata["inspect_status"], "success")

    @unittest.skipUnless(inspect_available(), "optional Inspect dependency is absent")
    def test_redundant_post_finish_calls_are_not_violations(self) -> None:
        from inspect_ai.model import ModelOutput, get_model

        outputs = [
            ModelOutput.for_tool_call("mock", "inspect_dns", {"reasoning": "inspect"}),
            ModelOutput.for_tool_call("mock", "probe_dns", {"reasoning": "confirm"}),
            ModelOutput.for_tool_call("mock", "repair_dns", {"reasoning": "repair"}),
            ModelOutput.for_tool_call("mock", "probe_dns", {"reasoning": "verify"}),
            ModelOutput.for_tool_call("mock", "finish", {"reasoning": "healthy"}),
            ModelOutput.for_tool_call("mock", "finish", {"reasoning": "healthy"}),
            ModelOutput.for_tool_call("mock", "probe_dns", {"reasoning": "late probe"}),
            ModelOutput.for_tool_call("mock", "finish", {"reasoning": "healthy"}),
            ModelOutput.from_content("mock", "done"),
        ]
        model = get_model("mockllm/model", custom_outputs=outputs, memoize=False)
        observations = [
            {"nameserver": "192.0.2.1"},
            {"healthy": False},
            {"repaired": True},
            {"healthy": True},
        ]
        with TemporaryDirectory() as directory, patch(
            "benchmark_agent.inspect_runner.post_action",
            side_effect=observations,
        ) as adapter:
            trace, _ = run_inspect_candidate_evaluation(
                adapter_url="http://adapter.invalid",
                agent_view={"objective": "repair DNS", "service": "node"},
                log_dir=Path(directory),
                scenario=load_scenario(_SCENARIO),
                model=model,
                max_calls=6,
            )
        self.assertEqual(
            [item["action"] for item in trace],
            ["inspect_dns", "probe_dns", "repair_dns", "probe_dns", "finish"],
        )
        self.assertFalse(
            any(item.get("observation", {}).get("rejected") for item in trace)
        )
        # Post-finish calls are acknowledged without touching the Adapter.
        self.assertEqual(adapter.call_count, 4)


if __name__ == "__main__":
    unittest.main()
