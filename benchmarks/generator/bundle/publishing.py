"""Multi-dimensional scoring and immutable public/private release publishing."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Mapping

from generator.bundle.models import CompiledBenchmarkBundle


SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def score_submission(
    evidence: Mapping[str, Any], *, time_budget_seconds: float = 300.0,
) -> Dict[str, Any]:
    """Score solver evidence without conflating lifecycle health and diagnosis."""
    required = {"diagnosis", "repair", "tests", "elapsed_seconds", "side_effects", "operations"}
    if set(evidence) != required:
        raise ValueError("submission evidence has invalid fields")
    tests = list(evidence["tests"])
    functional = sum(bool(item.get("passed")) for item in tests) / max(1, len(tests))
    diagnosis = max(0.0, min(1.0, float(evidence["diagnosis"])))
    repair = max(0.0, min(1.0, float(evidence["repair"])))
    elapsed = max(0.0, float(evidence["elapsed_seconds"]))
    efficiency = max(0.0, 1.0 - elapsed / max(1.0, time_budget_seconds))
    side_effects = max(0, int(evidence["side_effects"]))
    operations = max(0, int(evidence["operations"]))
    safety = 1.0 / (1.0 + side_effects)
    economy = 1.0 / (1.0 + max(0, operations - 1) / 10.0)
    dimensions = {
        "diagnosis": diagnosis, "repair": repair, "functional": functional,
        "efficiency": efficiency, "safety": safety, "operation_economy": economy,
    }
    weights = {
        "diagnosis": 0.25, "repair": 0.25, "functional": 0.25,
        "efficiency": 0.10, "safety": 0.10, "operation_economy": 0.05,
    }
    total = round(sum(dimensions[key] * weights[key] for key in weights), 6)
    result: Dict[str, Any] = {
        "schema_version": 1, "dimensions": dimensions, "weights": weights,
        "total_score": total, "passed": total >= 0.75 and functional == 1.0,
    }
    result["score_fingerprint"] = _sha_bytes(_canonical(result))
    return result


class ReleaseRegistry:
    def __init__(self, path: Path):
        self.path = path.resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if not self.path.exists(): return {"schema_version": 1, "releases": {}}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1: raise ValueError("invalid release registry")
        return value

    def register(self, manifest: Mapping[str, Any]) -> None:
        value = self.load(); key = f"{manifest['benchmark_id']}@{manifest['version']}"
        current = value["releases"].get(key)
        if current and current["release_fingerprint"] != manifest["release_fingerprint"]:
            raise ValueError("release version is immutable")
        if current: return
        value["releases"][key] = dict(manifest)
        _atomic_json(self.path, value, 0o600)


def _atomic_json(path: Path, value: Mapping[str, Any], mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path); os.chmod(path, mode)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def publish_bundle(
    bundle: CompiledBenchmarkBundle, *, version: str,
    public_root: Path, private_root: Path, registry: ReleaseRegistry,
    quality_report: Mapping[str, Any], qualification: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    if not SEMVER.fullmatch(version): raise ValueError("release version must be semver")
    public_root, private_root = public_root.resolve(), private_root.resolve()
    if public_root == private_root or public_root in private_root.parents or private_root in public_root.parents:
        raise ValueError("public and private release roots must be disjoint")
    if quality_report.get("passed") is not True:
        raise ValueError("release requires a passing quality report")
    if not qualification or qualification.get("status") != "qualified":
        raise ValueError("release requires formal qualification")
    release_id = f"{bundle.benchmark_id}-{version}"
    public_path = public_root / release_id / "bundle.json"
    private_path = private_root / release_id / "bundle.json"
    _atomic_json(public_path, bundle.public_bundle, 0o644)
    _atomic_json(private_path, bundle.private_bundle, 0o600)
    manifest: Dict[str, Any] = {
        "schema_version": 1, "benchmark_id": bundle.benchmark_id,
        "version": version, "bundle_fingerprint": bundle.bundle_fingerprint,
        "generator_contract_sha256": bundle.generator_contract_sha256,
        "quality_fingerprint": quality_report["quality_fingerprint"],
        "qualification_sha256": qualification.get("qualification_sha256", ""),
        "public_sha256": _sha_bytes(public_path.read_bytes()),
        "private_sha256": _sha_bytes(private_path.read_bytes()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest["release_fingerprint"] = _sha_bytes(_canonical(manifest))
    _atomic_json(public_path.parent / "release.json", manifest, 0o644)
    registry.register(manifest)
    return {**manifest, "public_path": str(public_path), "private_path": str(private_path)}
