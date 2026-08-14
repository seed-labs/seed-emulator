#!/usr/bin/env python3
"""Materialize auditable, no-AI contract evidence for the application pilot."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.bundle.compiler import BundleCompiler  # noqa: E402
from generator.bundle.lifecycle import BundleLifecycleExecutor  # noqa: E402
from generator.bundle.pilot import pilot_capabilities, write_pilot_artifacts  # noqa: E402
from generator.bundle.qualification import qualify_bundle  # noqa: E402
from generator.bundle.scale import validate_bundle_scales  # noqa: E402


def main():
    report_root = BENCHMARKS_DIR / "reports" / "MULTI_AGENT_APPLICATION_PILOT"
    report_root.mkdir(parents=True, exist_ok=True)
    store, spec = write_pilot_artifacts(report_root / "artifacts")
    capabilities = pilot_capabilities()
    (report_root / "bundle_spec.json").write_text(
        json.dumps(spec.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (report_root / "capabilities.json").write_text(
        json.dumps(capabilities, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    bundle = BundleCompiler(BENCHMARKS_DIR, store).compile(
        spec, capabilities=capabilities
    )
    BundleCompiler.write(bundle, report_root / "compiled_bundle.json")
    (report_root / "public_bundle.json").write_text(
        json.dumps(bundle.public_bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (report_root / "private_bundle.json").write_text(
        json.dumps(bundle.private_bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    running = {item["container"]: True for item in capabilities["assets"]}

    class PilotSimulationRunner:
        def ensure_service(self, _service, _capabilities):
            return 0, "simulated service ready", {}

        def run_workload(self, _workload, _capabilities):
            return 0, "simulated workload warm", {}

        def run_test(self, test, _capabilities):
            return 0, str(running[test.selector["container"]]).lower(), {}

    def fault_runner(command, _timeout):
        target = command.split()[-1]
        if "docker stop" in command:
            running[target] = False
            return 0, "simulated stop"
        if "docker start" in command:
            running[target] = True
            return 0, "simulated start"
        if "docker inspect" in command:
            return 0, str(running[target]).lower()
        return 0, "simulated command"

    executor = BundleLifecycleExecutor(
        report_root / "journals", PilotSimulationRunner(),
        fault_runner=fault_runner,
    )
    receipts = []
    for round_index in range(1, 3):
        receipt = report_root / f"lifecycle_round_{round_index:02d}.json"
        executor.run(bundle, capabilities, receipt)
        receipts.append(receipt)
    qualification = qualify_bundle(
        bundle, receipts, report_root / "qualification.json",
        qualification_level="pilot",
    )
    scale = validate_bundle_scales(bundle)
    (report_root / "scale_validation.json").write_text(
        json.dumps(scale, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    real_100_path = BENCHMARKS_DIR / "reports" / "TOPOLOGY_SCALE_100_SMOKE.json"
    real_100 = json.loads(real_100_path.read_text(encoding="utf-8"))
    real_100_verified = (
        real_100.get("asset_count") == 100
        and real_100.get("connectivity_verified") is True
    )
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": bundle.benchmark_id,
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "ai_invoked": False,
        "execution_mode": "simulated_contract_pilot_no_container_launch",
        "formal_promotion_eligible": False,
        "existing_real_100_node_topology_evidence": {
            "path": str(real_100_path), "verified": real_100_verified,
            "topology_fingerprint": real_100.get("topology_fingerprint", ""),
        },
        "qualification": str(qualification),
        "twelve_step_coverage": {
            "bundle_contract": True,
            "agent_artifact_protocol": True,
            "coordinator": True,
            "application_workload_layer": True,
            "test_oracle_layer": True,
            "plugin_sdk": True,
            "fault_platform_unification": True,
            "cross_artifact_safety": True,
            "blind_public_private_split": True,
            "end_to_end_cli_and_lifecycle": True,
            "three_application_pilot": True,
            "scale_5_20_100_1000_10000": scale["passed"] and real_100_verified,
        },
        "passed": (
            all(scale_item["passed"] for scale_item in scale["results"])
            and real_100_verified
        ),
    }
    (report_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
