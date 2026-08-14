#!/usr/bin/env python3
"""Run the versioned NL intent, clarification, extension and attack corpus."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.nl.audit import atomic_json, nl_contract_sha256  # noqa: E402
from generator.nl.provider import DeterministicLLMProvider  # noqa: E402
from generator.nl.schema import (  # noqa: E402
    BENCHMARK_INTENT_OUTPUT_SCHEMA, validate_provider_output,
)
from generator.nl.security import inspect_natural_language  # noqa: E402
from generator.nl.session import NaturalLanguagePlanner, validate_blind_receipt  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=BENCHMARKS_DIR / "reports/NL_GENERATOR_REGRESSION.json",
    )
    args = parser.parse_args(argv)
    fixture_path = BENCHMARKS_DIR / "tests/fixtures/nl_benchmark_cases.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    results = []
    provider = DeterministicLLMProvider()
    with tempfile.TemporaryDirectory(prefix="nl-regression-") as temporary:
        planner = NaturalLanguagePlanner(BENCHMARKS_DIR, Path(temporary))
        for index, case in enumerate(fixture["intent_cases"]):
            result = planner.plan(
                case["text"], provider=provider,
                seed=f"regression-{case['case_id']}",
                session_id=f"case_{index:03d}_{case['case_id']}",
            )
            passed = result["status"] == case["expected_status"]
            if result["status"] == "ready":
                intent = json.loads(Path(result["approved_intent"]).read_text())
                passed = passed and intent["applications"] == case["expected_applications"]
                passed = passed and intent["fault_types"] == case["expected_faults"]
            results.append({
                "case_id": case["case_id"], "expected": case["expected_status"],
                "actual": result["status"], "passed": passed,
            })
    for index, text in enumerate(fixture["prompt_injection_cases"]):
        report = inspect_natural_language(text)
        results.append({
            "case_id": f"prompt_injection_{index:03d}", "expected": "blocked",
            "actual": "blocked" if not report.allowed else "allowed",
            "passed": not report.allowed,
        })
    baseline = provider.complete_structured(
        [{"role": "user", "content": fixture["intent_cases"][0]["text"]}],
        BENCHMARK_INTENT_OUTPUT_SCHEMA,
        seed="structured-output-attacks",
    ).output
    for case in fixture["structured_output_attacks"]:
        attack = {**baseline, case["field"]: case["value"]}
        try:
            validate_provider_output(attack)
            rejected = False
        except ValueError:
            rejected = True
        results.append({
            "case_id": case["attack_id"], "expected": "schema_rejected",
            "actual": "schema_rejected" if rejected else "accepted",
            "passed": rejected,
        })
    for case in fixture["blind_receipt_attacks"]:
        receipt = {
            "ai_invoked": False, "blind_mode": True,
            "passed": True, "topology_tainted": False,
            case["field"]: case["value"],
        }
        try:
            validate_blind_receipt(receipt)
            rejected = False
        except RuntimeError:
            rejected = True
        results.append({
            "case_id": case["attack_id"], "expected": "receipt_rejected",
            "actual": "receipt_rejected" if rejected else "accepted",
            "passed": rejected,
        })
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nl_contract_sha256": nl_contract_sha256(),
        "fixture": str(fixture_path),
        "results": results,
        "passed": all(item["passed"] for item in results),
    }
    atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
