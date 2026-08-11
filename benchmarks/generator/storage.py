"""Atomic, benchmark-local persistence for generated suite manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from generator.models import SuiteManifest
from generator.validator import validate_manifest


def suite_manifest_path(benchmarks_dir: Path, suite_id: str) -> Path:
    root = benchmarks_dir.resolve()
    destination = (root / "specs" / suite_id / "manifest.json").resolve()
    try:
        destination.relative_to(root / "specs")
    except ValueError as exc:
        raise ValueError("suite destination escapes benchmarks/specs") from exc
    return destination


def write_manifest(
    benchmarks_dir: Path,
    manifest: SuiteManifest,
    *,
    force: bool = False,
) -> Path:
    validate_manifest(manifest)
    destination = suite_manifest_path(benchmarks_dir, manifest.suite_id)
    if destination.exists() and not force:
        raise FileExistsError(
            f"suite already exists: {destination}; use --force to replace it"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        manifest.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".manifest.",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return destination


def validate_manifest_file(path: Path) -> SuiteManifest:
    value = json.loads(path.resolve().read_text(encoding="utf-8"))
    manifest = SuiteManifest.from_dict(value)
    validate_manifest(manifest)
    return manifest
