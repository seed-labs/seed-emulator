#!/usr/bin/env python3
"""Refresh quarantined suite contracts after audited generator changes.

Promoted suites are deliberately demoted. They must collect new lifecycle
receipts and pass the normal promotion command again; this utility never edits
or manufactures promotion evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.contracts import inspect_contracts  # noqa: E402
from generator.models import SuiteManifest  # noqa: E402
from generator.validator import validate_manifest  # noqa: E402


def refresh(root: Path = BENCHMARKS_DIR):
    contract = inspect_contracts(root).sha256
    changed = []
    for path in sorted((root / "specs").glob("*/manifest.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        was_promoted = any(
            item.get("main_score_eligible") is True
            for item in value.get("scenarios", ())
        )
        value["contract_sha256"] = contract
        if was_promoted:
            for item in value.get("scenarios", ()):
                item["main_score_eligible"] = False
                item["quarantine_reason"] = (
                    "generator contract changed; collect fresh blind no-AI "
                    "lifecycle evidence before re-promotion"
                )
        manifest = SuiteManifest.from_dict(value)
        validate_manifest(manifest)
        payload = json.dumps(
            manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n"
        descriptor, temporary = tempfile.mkstemp(
            prefix=".manifest.contract-refresh.", suffix=".tmp",
            dir=path.parent, text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            raise
        changed.append({"suite_id": manifest.suite_id, "demoted": was_promoted})
    return {"contract_sha256": contract, "suites": changed}


if __name__ == "__main__":
    print(json.dumps(refresh(), indent=2, sort_keys=True))
