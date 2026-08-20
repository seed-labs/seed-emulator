#!/usr/bin/env python3
"""Tiered CI entry point for the production benchmark generator."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.bundle.scheduler import continuous_validation_matrix  # noqa: E402
from generator.contracts import inspect_contracts  # noqa: E402


TIERS = {
    "per-commit": {5, 20},
    "nightly": {5, 20, 100},
    "weekly": {5, 20, 100, 1000, 10000},
}


def _run(path: str) -> dict:
    result = subprocess.run(
        [sys.executable, path], cwd=BENCHMARKS_DIR,
        capture_output=True, text=True, timeout=180,
    )
    return {
        "test": path, "exit_code": result.returncode,
        "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-2000:],
        "passed": result.returncode == 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=tuple(TIERS), default="per-commit")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    snapshot = inspect_contracts(BENCHMARKS_DIR)
    tests = [
        _run("tests/test_production_generator.py"),
        _run("tests/test_multi_agent_bundle.py"),
        _run("tests/test_fault_injection_platform.py"),
        _run("tests/test_topology_generator.py"),
        _run("tests/test_natural_language_generator.py"),
        _run("tests/test_unsafe_natural_language_generator.py"),
    ]
    matrix = continuous_validation_matrix()
    selected = [row for row in matrix["rows"] if row["scale"] in TIERS[args.tier]]
    application_qualification = json.loads((
        BENCHMARKS_DIR / "reports" / "PRODUCTION_APPLICATION_E2E_V2" /
        "qualification.json"
    ).read_text(encoding="utf-8"))
    evidence = [{
        "scale": 5, "mode": "real_full",
        "passed": (
            application_qualification.get("status") == "qualified"
            and application_qualification.get("generator_contract_sha256")
            == snapshot.sha256
            and len(application_qualification.get("receipts", ())) >= 2
        ),
        "qualification_sha256": application_qualification.get(
            "qualification_sha256"
        ),
    }]
    if args.tier in {"nightly", "weekly"}:
        value = json.loads(
            (BENCHMARKS_DIR / "reports" / "TOPOLOGY_SCALE_100_SMOKE.json").read_text(
                encoding="utf-8"
            )
        )
        evidence.append({
            "scale": 100, "mode": "real_full",
            "passed": value.get("connectivity_verified") is True,
            "topology_fingerprint": value.get("topology_fingerprint"),
        })
    if args.tier == "weekly":
        for scale in (1000, 10000):
            value = json.loads((
                BENCHMARKS_DIR / "reports" /
                f"FAULT_PLATFORM_SCALE_{scale}_VALIDATION.json"
            ).read_text(encoding="utf-8"))
            results = list(value.get("results", ()))
            evidence.append({
                "scale": scale, "mode": "plan_performance_sampled",
                "passed": bool(results) and all(
                    item.get("passed") is True
                    and item.get("execution_mode") == "plan_only_no_container_launch"
                    and item.get("asset_count") == scale
                    for item in results
                ),
                "execution_mode": "plan_only_no_container_launch",
            })
    report = {
        "schema_version": 1, "tier": args.tier,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_contract_sha256": snapshot.sha256,
        "selected_matrix": selected, "tests": tests, "scale_evidence": evidence,
    }
    report["passed"] = all(item["passed"] for item in tests + evidence)
    output = Path(args.output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
