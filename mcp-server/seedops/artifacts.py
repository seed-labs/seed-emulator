from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store import ArtifactRow, SeedOpsStore


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "artifact"
    name = name.replace(os.sep, "_")
    name = name.replace("/", "_")
    name = _SAFE_NAME_RE.sub("_", name)
    return name[:120] or "artifact"


@dataclass(frozen=True)
class ArtifactReadResult:
    artifact: ArtifactRow
    content: str
    truncated: bool


class ArtifactManager:
    """Manage on-disk artifacts with metadata in SQLite."""

    def __init__(self, *, base_dir: str, store: SeedOpsStore):
        self._base_dir = Path(base_dir)
        self._store = store
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self._base_dir / workspace_id

    def _job_artifacts_dir(self, workspace_id: str, job_id: str) -> Path:
        return self._workspace_dir(workspace_id) / "artifacts" / job_id

    def write_json(self, *, workspace_id: str, job_id: str, name: str, data: Any) -> ArtifactRow:
        safe = _safe_name(name)
        out_dir = self._job_artifacts_dir(workspace_id, job_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{safe}.json"

        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)

        size = path.stat().st_size
        artifact_id = str(uuid.uuid4())
        self._store.insert_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            workspace_id=workspace_id,
            name=safe,
            kind="json",
            path=str(path),
            size_bytes=int(size),
        )

        row = self._store.get_artifact(artifact_id)
        assert row is not None
        return row

    def read(self, artifact_id: str, *, max_chars: int = 8000) -> ArtifactReadResult | None:
        row = self._store.get_artifact(artifact_id)
        if row is None:
            return None

        p = Path(row.path)
        if not p.exists():
            return ArtifactReadResult(artifact=row, content="[missing artifact file]", truncated=False)

        if max_chars <= 0:
            return ArtifactReadResult(artifact=row, content="", truncated=False)

        raw = p.read_text(encoding="utf-8", errors="replace")
        if len(raw) <= max_chars:
            return ArtifactReadResult(artifact=row, content=raw, truncated=False)
        return ArtifactReadResult(artifact=row, content=raw[:max_chars] + "\n...[truncated]", truncated=True)

