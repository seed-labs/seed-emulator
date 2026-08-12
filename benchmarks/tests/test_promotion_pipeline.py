"""Promotion requires independent clean evidence and detects tampering."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

import generator.promotion as promotion  # noqa: E402
from generator.storage import validate_manifest_file  # noqa: E402
from generator.topology.registry import load_plan  # noqa: E402


SOURCE = BENCHMARKS_DIR / "specs" / "declarative_small_ring_pilot" / "manifest.json"
source_manifest = validate_manifest_file(SOURCE)
quarantined_manifest = replace(
    source_manifest,
    scenarios=tuple(
        replace(
            item,
            benchmark_track="robustness",
            main_score_eligible=False,
            quarantine_reason="promotion test quarantine",
        )
        for item in source_manifest.scenarios
    ),
)
plan = load_plan("small_ring")


def result_rows(manifest, *, clean=True):
    return [
        {
            "scenario": item.name,
            "generation_fingerprint": item.fingerprint,
            "generation_contract_sha256": manifest.contract_sha256,
            "generated_suite_id": manifest.suite_id,
            "topology": item.topology,
            "healthy_baseline_verified": clean,
            "fault_injection_verified": clean,
            "fix_verified": clean,
            "standard_cleanup_verified": clean,
            "topology_tainted": not clean,
        }
        for item in manifest.scenarios
    ]


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    manifest_path = root / "specs" / source_manifest.suite_id / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(quarantined_manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    reports = root / "reports"
    reports.mkdir()
    smoke = reports / "smoke.json"
    smoke.write_text(json.dumps({
        "topology_id": "small_ring",
        "topology_fingerprint": plan.fingerprint,
        "connectivity_verified": True,
    }) + "\n", encoding="utf-8")
    observation = reports / "observation.json"
    observation.write_text(json.dumps({
        "topology_id": "small_ring",
        "topology_fingerprint": plan.fingerprint,
        "capture_profile": "declarative_capability_driven",
        "scenario_metadata_included": False,
        "probe_count": 3,
        "observations": {"probe": {"output": "healthy"}},
    }) + "\n", encoding="utf-8")
    receipt1, receipt2 = reports / "round1.json", reports / "round2.json"
    for receipt in (receipt1, receipt2):
        promotion.write_lifecycle_receipt(
            receipt, result_rows(quarantined_manifest),
            agent_type="rule", blind_mode=True, validate_only=True,
        )
    original_inspect = promotion.inspect_contracts
    promotion.inspect_contracts = lambda _root: type(
        "Snapshot", (), {"sha256": quarantined_manifest.contract_sha256}
    )()
    try:
        record_path = promotion.promote_suite(
            root, source_manifest.suite_id, [receipt1, receipt2],
            topology_evidence=smoke, observation_evidence=observation,
        )
        promoted = validate_manifest_file(manifest_path)
        assert all(item.main_score_eligible for item in promoted.scenarios)
        assert all(not item.quarantine_reason for item in promoted.scenarios)
        assert {item.benchmark_track for item in promoted.scenarios} == {
            "network_functional", "network_control_plane"
        }
        promotion.verify_promotion_record(root, promoted)

        # A single bit of evidence drift must invalidate an already promoted suite.
        receipt1.write_text(receipt1.read_text() + " ", encoding="utf-8")
        try:
            promotion.verify_promotion_record(root, promoted)
            raise AssertionError("tampered receipt was accepted")
        except ValueError as exc:
            assert "modified" in str(exc)
        receipt1.write_text(receipt1.read_text()[:-1], encoding="utf-8")

        # Removing the record cannot silently turn a generated case into main score.
        record_path.unlink()
        try:
            promotion.verify_promotion_record(root, promoted)
            raise AssertionError("promoted manifest without record was accepted")
        except ValueError as exc:
            assert "no promotion record" in str(exc)
    finally:
        promotion.inspect_contracts = original_inspect

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    manifest_path = root / "specs" / source_manifest.suite_id / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(quarantined_manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    reports = root / "reports"
    reports.mkdir()
    smoke = reports / "smoke.json"
    smoke.write_text(json.dumps({
        "topology_id": "small_ring",
        "topology_fingerprint": plan.fingerprint,
        "connectivity_verified": True,
    }), encoding="utf-8")
    observation = reports / "observation.json"
    observation.write_text(json.dumps({
        "topology_id": "small_ring",
        "topology_fingerprint": plan.fingerprint,
        "capture_profile": "declarative_capability_driven",
        "scenario_metadata_included": False,
        "probe_count": 1,
        "observations": {"probe": {}},
    }), encoding="utf-8")
    failed = reports / "failed.json"
    promotion.write_lifecycle_receipt(
        failed, result_rows(quarantined_manifest, clean=False),
        agent_type="rule", blind_mode=True, validate_only=True,
    )
    original_inspect = promotion.inspect_contracts
    promotion.inspect_contracts = lambda _root: type(
        "Snapshot", (), {"sha256": quarantined_manifest.contract_sha256}
    )()
    try:
        try:
            promotion.promote_suite(
                root, source_manifest.suite_id, [failed, failed],
                topology_evidence=smoke, observation_evidence=observation,
            )
            raise AssertionError("failed/duplicate evidence was accepted")
        except ValueError:
            pass
        assert not any(
            item.main_score_eligible
            for item in validate_manifest_file(manifest_path).scenarios
        )
    finally:
        promotion.inspect_contracts = original_inspect
