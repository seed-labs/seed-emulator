"""Deterministic benchmark quality gates and duplicate prevention."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Iterable, Mapping, Sequence

from generator.bundle.models import CompiledBenchmarkBundle
from generator.bundle.request import BenchmarkRequest


DIFFICULTY_RANGES = {
    "easy": (0.00, 0.40), "medium": (0.20, 0.65),
    "hard": (0.40, 0.85), "expert": (0.60, 1.00),
}


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def select_fault_combination(
    candidates: Sequence[Mapping[str, Any]], count: int,
) -> tuple[Mapping[str, Any], ...]:
    """Greedy deterministic set-cover over drivers, assets and expectations."""
    if not 1 <= count <= len(candidates):
        raise ValueError("fault combination count is outside candidate range")
    remaining = sorted(candidates, key=lambda item: str(item["candidate_id"]))
    selected, covered = [], set()
    while len(selected) < count:
        ranked = []
        for item in remaining:
            features = {
                f"driver:{item['fault_type']}", f"asset:{item['asset']}",
                *(f"expectation:{x}" for x in item.get("must_break", ())),
            }
            ranked.append((len(features - covered), str(item["candidate_id"]), item, features))
        _gain, _identity, chosen, features = sorted(
            ranked, key=lambda row: (-row[0], row[1])
        )[0]
        selected.append(chosen); covered.update(features); remaining.remove(chosen)
    return tuple(selected)


def assess_bundle(
    bundle: CompiledBenchmarkBundle, request: BenchmarkRequest,
) -> Dict[str, Any]:
    private = bundle.private_bundle
    tests = list(private["tests"])
    plans = list(private["fault_plans"])
    actions = [action for plan in plans for action in plan["actions"]]
    must_break = list(private.get("must_break", ()))
    must_preserve = list(private.get("must_preserve", ()))
    active = [item for item in tests if item["phase"] == "active"]
    recovery = [item for item in tests if item["phase"] == "recovery"]
    active_expectations = {item["expectation_id"] for item in active}
    recovery_expectations = {item["expectation_id"] for item in recovery}
    root_counts = {item: must_break.count(item) for item in set(must_break)}
    unique_roots = bool(root_counts) and all(value == 1 for value in root_counts.values())
    observable = set(must_break) <= active_expectations
    recoverable = set(must_break) <= recovery_expectations
    preserved = set(must_preserve) <= active_expectations
    drivers = {item["driver"] for item in actions}
    assets = {target for item in actions for target in item["targets"]}
    interaction = max(0, len(actions) - 1)
    scale_factor = min(1.0, request.scale / 100.0)
    score = min(1.0, round(
        0.16 * min(1.0, len(actions) / 4.0)
        + 0.16 * min(1.0, len(drivers) / 3.0)
        + 0.14 * min(1.0, len(assets) / 4.0)
        + 0.16 * min(1.0, interaction / 3.0)
        + 0.12 * min(1.0, len(active) / 8.0)
        + 0.10 * scale_factor
        + 0.08 * float(bool(must_preserve))
        + 0.08 * float(len(plans) > 0), 4
    ))
    lower, upper = DIFFICULTY_RANGES[request.difficulty]
    checks = {
        "compiler_safety_approved": bundle.safety_review.get("approved") is True,
        "must_break_observable": observable,
        "must_break_recoverable": recoverable,
        "must_preserve_observable": preserved,
        "root_cause_expectations_unique": unique_roots,
        "fault_count_matches_request": len(actions) == request.fault_count,
        "difficulty_in_requested_band": lower <= score <= upper,
        "public_private_isolation": bundle.public_bundle.get(
            "scenario_metadata_included"
        ) is False,
    }
    signature = {
        "topology": bundle.topology_fingerprint,
        "drivers": sorted(drivers), "assets": sorted(assets),
        "must_break": sorted(must_break), "must_preserve": sorted(must_preserve),
        "tests": sorted((item["phase"], item["driver"], item["expectation_id"]) for item in tests),
    }
    report: Dict[str, Any] = {
        "schema_version": 1, "benchmark_id": bundle.benchmark_id,
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "request_fingerprint": request.fingerprint,
        "difficulty": request.difficulty, "difficulty_score": score,
        "difficulty_band": [lower, upper], "fault_driver_diversity": len(drivers),
        "affected_asset_diversity": len(assets), "interaction_count": interaction,
        "checks": checks, "scenario_signature": _sha(signature),
        "passed": all(checks.values()),
    }
    report["quality_fingerprint"] = _sha(report)
    return report


class QualityIndex:
    """Atomic revision index; signatures cannot change benchmark owners."""

    def __init__(self, path: Path):
        self.path = path.resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "entries": {}}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1 or not isinstance(value.get("entries"), dict):
            raise ValueError("invalid quality index")
        return value

    def register(self, report: Mapping[str, Any]) -> None:
        if report.get("passed") is not True:
            raise ValueError("cannot register a failed quality report")
        value = self.load(); signature = str(report["scenario_signature"])
        current = value["entries"].get(signature)
        revision = {
            "bundle_fingerprint": report["bundle_fingerprint"],
            "quality_fingerprint": report["quality_fingerprint"],
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        if current and current["benchmark_id"] != report["benchmark_id"]:
            raise ValueError(
                f"duplicate scenario signature already owned by {current['benchmark_id']}"
            )
        if current:
            revisions = list(current.get("revisions", ()))
            if not revisions and current.get("bundle_fingerprint"):
                revisions.append({
                    key: current[key] for key in (
                        "bundle_fingerprint", "quality_fingerprint", "registered_at"
                    )
                })
                for key in ("bundle_fingerprint", "quality_fingerprint", "registered_at"):
                    current.pop(key, None)
            if any(
                item["bundle_fingerprint"] == revision["bundle_fingerprint"]
                for item in revisions
            ):
                return
            revisions.append(revision); current["revisions"] = revisions
            current["latest_bundle_fingerprint"] = revision["bundle_fingerprint"]
        else:
            value["entries"][signature] = {
                "benchmark_id": report["benchmark_id"],
                "latest_bundle_fingerprint": revision["bundle_fingerprint"],
                "revisions": [revision],
            }
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except Exception:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            raise
