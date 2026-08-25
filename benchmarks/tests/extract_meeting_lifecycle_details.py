#!/usr/bin/env python3
"""Extract compact, human-reviewable evidence from meeting lifecycle workspaces."""

from __future__ import annotations

import json
from pathlib import Path
import sys


root = Path(sys.argv[1]).resolve()
output = {}
for workspace in sorted((root / "lifecycles").iterdir()):
    if not (workspace / "summary.json").is_file():
        continue
    bundle = json.loads((workspace / "compiled_bundle.json").read_text())
    receipt = json.loads((workspace / "lifecycle_round_01.json").read_text())
    actions = []
    for plan in bundle["private_bundle"]["fault_plans"]:
        for action in plan["actions"]:
            actions.append({
                key: action.get(key)
                for key in (
                    "action_id", "driver", "artifact", "inject_order",
                    "cleanup_order", "depends_on", "expected_value", "faulty_value",
                )
            })
    tests = []
    for test in receipt["tests"]:
        evidence = test.get("evidence", [])
        rendered = "\n".join(str(item.get("output", "")) for item in evidence)
        tests.append({
            "test_id": test["test_id"],
            "phase": test["phase"],
            "passed": test["passed"],
            "exit_codes": [item.get("exit_code") for item in evidence],
            "output_excerpt": rendered[:280],
        })
    output[workspace.name] = {
        "fault_actions": actions,
        "round_01": {
            "passed": receipt["passed"],
            "ai_invoked": receipt["ai_invoked"],
            "convergence": receipt["convergence"],
            "tests": tests,
            "cleanup_failures": receipt["cleanup_failures"],
        },
    }

target = root / "raw" / "lifecycle_details.json"
target.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    name: {
        "drivers": [item["driver"] for item in value["fault_actions"]],
        "passed": value["round_01"]["passed"],
        "convergence": value["round_01"]["convergence"]["passed"],
    }
    for name, value in output.items()
}, ensure_ascii=False, indent=2, sort_keys=True))
