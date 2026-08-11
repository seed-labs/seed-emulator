"""Regression checks for the benchmark CLI blind repair context."""

import sys
import types
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))


class _Stats:
    total_calls = 1
    successful_calls = 1
    failed_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_latency_ms = 0
    calls = []


class _Diagnosis:
    category = "unknown"
    confidence = 0.0
    root_cause = "unknown"
    repair_commands = []
    target_container = []
    artifact = ""
    faulty_value = ""
    expected_value = ""


class _Agent:
    last_context = None
    last_max_turns = None

    def __init__(self, max_turns, **_kwargs):
        _Agent.last_max_turns = max_turns
        self.api_stats = _Stats()
        self.turns_log = []

    def diagnose_interactive(self, task_context, repair_mode, **_kwargs):
        assert repair_mode is True
        _Agent.last_context = task_context
        return _Diagnosis()


class _Scenario:
    def get_repair_context(self):
        return "SECRET_SCENARIO_GROUND_TRUTH"


sys.modules["ai_agent"] = types.SimpleNamespace(AIAgent=_Agent)

from benchmark_cli import run_ai_repair  # noqa: E402


blind_result = run_ai_repair(_Scenario(), max_turns=7)
assert blind_result["blind_mode"] is True
assert blind_result["max_turns"] == 7
assert _Agent.last_max_turns == 7
assert "SECRET_SCENARIO_GROUND_TRUTH" not in _Agent.last_context

guided_result = run_ai_repair(_Scenario(), blind=False)
assert guided_result["blind_mode"] is False
assert _Agent.last_context == "SECRET_SCENARIO_GROUND_TRUTH"
