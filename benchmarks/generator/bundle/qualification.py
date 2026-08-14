"""Tamper-evident promotion evidence for complete BenchmarkBundles."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Mapping, Sequence

from generator.bundle.models import CompiledBenchmarkBundle


MIN_RUNS = 2


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify_bundle(
    bundle: CompiledBenchmarkBundle, receipt_paths: Sequence[Path], output: Path,
    *, qualification_level: str = "formal",
) -> Path:
    if qualification_level not in {"pilot", "formal"}:
        raise ValueError("unsupported qualification level")
    if len(receipt_paths) < MIN_RUNS:
        raise ValueError("bundle qualification requires two independent runs")
    receipts, run_ids = [], set()
    for path in receipt_paths:
        value = json.loads(path.resolve().read_text(encoding="utf-8"))
        supplied = str(value.pop("receipt_sha256", ""))
        expected = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if not supplied or supplied != expected:
            raise ValueError("lifecycle receipt fingerprint mismatch")
        value["receipt_sha256"] = supplied
        if value.get("bundle_fingerprint") != bundle.bundle_fingerprint:
            raise ValueError("lifecycle receipt targets another bundle")
        if value.get("generator_contract_sha256") != bundle.generator_contract_sha256:
            raise ValueError("lifecycle receipt targets another generator contract")
        if value.get("mode") != "no_ai" or value.get("blind_mode") is not True:
            raise ValueError("qualification requires blind no-AI receipts")
        if value.get("passed") is not True or value.get("topology_tainted") is True:
            raise ValueError("qualification receipt is not clean")
        if (
            qualification_level == "formal"
            and value.get("execution_backend") != "DockerLifecycleRunner"
        ):
            raise ValueError("formal qualification requires the real Docker lifecycle backend")
        run_id = str(value.get("run_id", ""))
        if not run_id or run_id in run_ids:
            raise ValueError("qualification requires unique run ids")
        run_ids.add(run_id)
        receipts.append({"path": str(path.resolve()), "sha256": _sha(path.resolve()), "run_id": run_id})
    payload: Dict[str, Any] = {
        "schema_version": 1, "benchmark_id": bundle.benchmark_id,
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "generator_contract_sha256": bundle.generator_contract_sha256,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "minimum_independent_runs": MIN_RUNS, "receipts": receipts,
        "qualification_level": qualification_level,
        "status": "qualified" if qualification_level == "formal" else "pilot_qualified",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["qualification_sha256"] = hashlib.sha256(canonical).hexdigest()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, output)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise
    return output
