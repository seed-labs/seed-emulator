#!/usr/bin/env python3
"""Run destructive-but-self-cleaning live scenario lifecycle contracts."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from scenarios import get_scenario  # noqa: E402
from scenarios.base import run  # noqa: E402


def validate_scenario(scenario):
    started = time.monotonic()
    result = {
        "scenario": scenario.name,
        "track": scenario.benchmark_track,
        "difficulty": scenario.difficulty,
        "scenario_seed": scenario.scenario_seed,
        "baseline_verified": False,
        "fault_verified": False,
        "cleanup_verified": False,
        "error": "",
    }
    try:
        scenario.prepare_healthy_baseline()
        result["baseline_verified"] = scenario.check_verified(
            run(scenario.get_verify_cmd(), timeout=30)
        )
        scenario.inject_fault()
        result["fault_verified"] = scenario.check_fault_active(
            run(scenario.get_verify_cmd(), timeout=30)
        )
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        run(scenario.get_fix_cmd(), timeout=120)
        deadline = time.monotonic() + scenario.convergence_timeout
        while time.monotonic() < deadline:
            if scenario.check_verified(
                run(scenario.get_verify_cmd(), timeout=30)
            ):
                result["cleanup_verified"] = True
                break
            time.sleep(3)
        result["duration_seconds"] = round(time.monotonic() - started, 1)
    result["passed"] = all(
        result[key]
        for key in (
            "baseline_verified",
            "fault_verified",
            "cleanup_verified",
        )
    )
    return result


def write_report(results, path):
    passed = sum(1 for result in results if result["passed"])
    lines = [
        "# Live Scenario Contract Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Passed: {passed}/{len(results)}",
        "",
        "| Scenario | Track | Baseline | Fault | Cleanup | Result |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for result in results:
        marker = lambda value: "PASS" if value else "FAIL"
        lines.append(
            f"| {result['scenario']} | {result['track']} | "
            f"{marker(result['baseline_verified'])} | "
            f"{marker(result['fault_verified'])} | "
            f"{marker(result['cleanup_verified'])} | "
            f"{marker(result['passed'])} |"
        )
    failures = [result for result in results if not result["passed"]]
    if failures:
        lines.extend(("", "## Failures", ""))
        for failure in failures:
            lines.append(
                f"- `{failure['scenario']}`: "
                f"{failure['error'] or 'contract condition failed'}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        required=True,
        help="Comma-separated scenario names",
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    results = []
    for name in (item.strip() for item in args.scenario.split(",")):
        scenario_class = get_scenario(name)
        if scenario_class is None:
            results.append(
                {
                    "scenario": name,
                    "track": "unknown",
                    "difficulty": "unknown",
                    "scenario_seed": None,
                    "baseline_verified": False,
                    "fault_verified": False,
                    "cleanup_verified": False,
                    "duration_seconds": 0,
                    "passed": False,
                    "error": "unknown scenario",
                }
            )
            continue
        print(f"VALIDATE {name}", flush=True)
        results.append(validate_scenario(scenario_class()))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, args.report)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(result["passed"] for result in results) else 1)


if __name__ == "__main__":
    main()
