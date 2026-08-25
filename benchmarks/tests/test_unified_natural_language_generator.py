#!/usr/bin/env python3
"""Unified arbitrary-benchmark planning contract tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.nl.unsafe_provider import DeterministicUnsafeProvider  # noqa: E402
from generator.nl.unified import (  # noqa: E402
    UnifiedNaturalLanguageExecutor,
    UnifiedNaturalLanguagePlanner,
)


def expect_error(function, expected=ValueError):
    try:
        function()
    except expected:
        return
    raise AssertionError(f"expected {expected.__name__}")


with tempfile.TemporaryDirectory(prefix="unified-nl-test-") as temporary:
    sessions = Path(temporary) / "sessions"
    result = UnifiedNaturalLanguagePlanner(BENCHMARKS_DIR, sessions).plan(
        "生成任意拓扑、软件、故障和恢复测试",
        provider=DeterministicUnsafeProvider(base_image="fixture-base:latest"),
        seed="unified-test-seed",
        session_id="unified_planner_test",
    )
    assert result["status"] == "ready"
    assert result["workflow"] == "arbitrary_benchmark_v1"
    assert result["execution_class"] == "isolated_arbitrary_code"
    assert result["preview"]["generated_dimensions"] == {
        "topology": True, "software": True, "faults": True, "tests": True,
    }
    assert result["preview"]["lifecycle"] == [
        "baseline", "inject", "observe", "recover", "verify",
    ]
    plan = Path(result["plan"])
    assert plan.name == "benchmark_plan.json"
    executor = UnifiedNaturalLanguageExecutor(BENCHMARKS_DIR, sessions)
    unsafe_path, value = executor._load_plan(plan)
    assert unsafe_path.name == "unsafe_plan.json"
    assert value["promotion_eligible"] is False

    tampered = json.loads(plan.read_text(encoding="utf-8"))
    tampered["deployment"] = "host"
    plan.write_text(json.dumps(tampered), encoding="utf-8")
    expect_error(lambda: executor._load_plan(plan))

print("unified natural-language generator tests: PASS")
