"""Wrong diagnosis categories must not block safe repair attempts."""

import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

import scenarios.base as base_module  # noqa: E402
import scenarios.strict_network_software as strict_module  # noqa: E402


class _Common:
    name = "authorization_regression"
    topology = "test"
    fault_type = "expected_category"
    settle_seconds = 0

    def prepare_healthy_baseline(self):
        pass

    def _capture_observation_state(self):
        return {"observations": {}}

    def inject_fault(self):
        pass

    def get_inject_cmd(self):
        return "inject"

    def get_verify_cmd(self):
        return "verify"

    def get_fix_cmd(self):
        return "cleanup"

    def check_verified(self, output):
        return output == "healthy"

    def verify_fix(self):
        return "healthy"

    def is_repair_command_allowed(self, command):
        return command == "safe-repair"


class _BaseScenario(_Common, base_module.BaseScenario):
    pass


class _StrictScenario(_Common, strict_module.StrictNetworkSoftwareScenario):
    def get_setup_cmd(self):
        return "setup"


def _wrong_category_repair(_scenario):
    return {
        "category": "wrong_category",
        "confidence": 0.9,
        "repair_commands": ["safe-repair", "unsafe-repair"],
    }


for scenario_type in (_BaseScenario, _StrictScenario):
    executed = []
    original_run = base_module.run
    original_sleep = base_module.time.sleep
    base_module.run = lambda command, timeout=0: executed.append(command) or "ok"
    base_module.time.sleep = lambda _seconds: None
    try:
        result = scenario_type().run_repair_evaluation(_wrong_category_repair)
    finally:
        base_module.run = original_run
        base_module.time.sleep = original_sleep

    assert result["correct_diagnosis"] is False
    assert result["repair_authorized"] is True
    assert result["repair_verified"] is True
    assert [item["command"] for item in result["repair_commands_executed"]] == [
        "safe-repair"
    ]
    assert result["repair_commands_rejected"] == ["unsafe-repair"]
    assert "safe-repair" in executed

    base_module.run = lambda command, timeout=0: "ok"
    base_module.time.sleep = lambda _seconds: None
    try:
        rejected_only = scenario_type().run_repair_evaluation(
            lambda _scenario: {
                "category": "wrong_category",
                "repair_commands": ["unsafe-repair"],
            }
        )
    finally:
        base_module.run = original_run
        base_module.time.sleep = original_sleep
    assert rejected_only["repair_submitted"] is True
    assert rejected_only["repair_authorized"] is False
    assert rejected_only["repair_verified"] is False
