#!/usr/bin/env python3
"""Run and formally qualify the three-application Bundle pilot on Docker."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.bundle.compiler import BundleCompiler  # noqa: E402
from generator.bundle.lifecycle import (  # noqa: E402
    BundleLifecycleExecutor, DockerLifecycleRunner,
)
from generator.bundle.pilot import write_pilot_artifacts  # noqa: E402
from generator.bundle.qualification import qualify_bundle  # noqa: E402
from generator.bundle.security import review_bundle  # noqa: E402
from generator.topology.bindings import load_capability_manifest  # noqa: E402


TOPOLOGY_ID = "multi_agent_application_pilot"


def main() -> int:
    report_dir = BENCHMARKS_DIR / "reports" / "MULTI_AGENT_APPLICATION_PILOT_REAL"
    report_dir.mkdir(parents=True, exist_ok=True)
    capabilities = load_capability_manifest(TOPOLOGY_ID)
    definition_sha = hashlib.sha256(
        (BENCHMARKS_DIR / "generator" / "bundle" / "pilot.py").read_bytes()
    ).hexdigest()[:16]
    store, spec = write_pilot_artifacts(
        report_dir / "artifacts" / definition_sha, capabilities
    )
    compiler = BundleCompiler(BENCHMARKS_DIR, store)
    bundle = compiler.compile(spec, capabilities=capabilities)
    compiler.write(bundle, report_dir / "compiled_bundle.json")
    (report_dir / "public_bundle.json").write_text(
        json.dumps(bundle.public_bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    review_bundle(
        public_bundle=bundle.public_bundle,
        private_bundle=bundle.private_bundle,
        forbidden_public_fields=bundle.private_bundle["blind_policy"][
            "forbidden_public_fields"
        ],
        known_assets=(item["container"] for item in capabilities["assets"]),
    )

    lifecycle = BundleLifecycleExecutor(
        report_dir / "journals", DockerLifecycleRunner()
    )
    receipts = []
    for index in range(1, 3):
        receipt = report_dir / f"lifecycle_round_{index:02d}.json"
        lifecycle.run(bundle, capabilities, receipt, blind_mode=True)
        receipts.append(receipt)
    qualification = qualify_bundle(
        bundle, receipts, report_dir / "qualification.json",
        qualification_level="formal",
    )
    receipt_values = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    summary = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": bundle.benchmark_id,
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "topology_fingerprint": bundle.topology_fingerprint,
        "applications": ["nginx", "bind9", "postgresql"],
        "fault_combination": [
            "container.stopped:nginx", "container.stopped:bind9",
            "container.stopped:postgresql",
        ],
        "application_protocol_probes": ["http", "dns", "postgresql_tcp"],
        "blind_mode": True,
        "ai_invoked": False,
        "real_docker_execution": True,
        "independent_clean_runs": len(receipts),
        "run_ids": [item["run_id"] for item in receipt_values],
        "all_runs_passed": all(
            item["passed"] and not item["topology_tainted"]
            for item in receipt_values
        ),
        "qualification": json.loads(qualification.read_text(encoding="utf-8")),
    }
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not summary["all_runs_passed"]:
        raise RuntimeError("real application pilot did not pass both lifecycle runs")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
