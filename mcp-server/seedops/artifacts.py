from __future__ import annotations

import base64
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store import ArtifactRow, SeedOpsStore


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_TRUNCATED_SUFFIX = "\n...[truncated]"
_MAX_CHUNK_BYTES = 256 * 1024


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


@dataclass(frozen=True)
class ArtifactChunkResult:
    artifact: ArtifactRow
    offset: int
    bytes_read: int
    file_size: int
    eof: bool
    content_b64: str


class ArtifactManager:
    """Manage on-disk artifacts with metadata in SQLite."""

    def __init__(self, *, base_dir: str, store: SeedOpsStore):
        self._base_dir = Path(base_dir)
        self._store = store
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_artifact_path(self, raw_path: str) -> Path:
        base = self._base_dir.resolve()
        p = Path(raw_path)
        # Resolve symlinks where possible. If the file does not exist, return the raw path.
        try:
            p_resolved = p.resolve()
        except FileNotFoundError:
            p_resolved = p.absolute()

        # Enforce that artifacts live under base_dir to avoid path traversal if DB is tampered.
        if base == p_resolved or base in p_resolved.parents:
            return p_resolved
        raise ValueError("Artifact path is outside of configured data directory.")

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

        p = self._resolve_artifact_path(row.path)
        if not p.exists():
            return ArtifactReadResult(artifact=row, content="[missing artifact file]", truncated=False)

        if max_chars <= 0:
            return ArtifactReadResult(artifact=row, content="", truncated=False)

        # Avoid reading entire file: cap bytes and decode as UTF-8 (replacement for invalid sequences).
        max_bytes = int(max_chars) * 4
        try:
            with open(p, "rb") as f:
                data = f.read(max_bytes + 1)
        except Exception:
            return ArtifactReadResult(artifact=row, content="[failed to read artifact file]", truncated=False)

        truncated = len(data) > max_bytes
        if truncated:
            data = data[:max_bytes]
        text = data.decode("utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars]
            truncated = True
        if truncated:
            text += _TRUNCATED_SUFFIX
        return ArtifactReadResult(artifact=row, content=text, truncated=truncated)

    def read_chunk_base64(
        self,
        artifact_id: str,
        *,
        offset: int = 0,
        max_bytes: int = 65536,
    ) -> ArtifactChunkResult | None:
        row = self._store.get_artifact(artifact_id)
        if row is None:
            return None

        if offset < 0:
            raise ValueError("offset must be >= 0")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be > 0")
        max_bytes_i = min(int(max_bytes), _MAX_CHUNK_BYTES)

        p = self._resolve_artifact_path(row.path)
        if not p.exists():
            return ArtifactChunkResult(
                artifact=row,
                offset=int(offset),
                bytes_read=0,
                file_size=0,
                eof=True,
                content_b64="",
            )

        file_size = int(p.stat().st_size)
        if int(offset) >= file_size:
            return ArtifactChunkResult(
                artifact=row,
                offset=int(offset),
                bytes_read=0,
                file_size=file_size,
                eof=True,
                content_b64="",
            )

        with open(p, "rb") as f:
            f.seek(int(offset))
            chunk = f.read(max_bytes_i)

        b64 = base64.b64encode(chunk).decode("ascii")
        bytes_read = len(chunk)
        eof = (int(offset) + bytes_read) >= file_size
        return ArtifactChunkResult(
            artifact=row,
            offset=int(offset),
            bytes_read=bytes_read,
            file_size=file_size,
            eof=eof,
            content_b64=b64,
        )

    def delete_files(self, artifacts: list[ArtifactRow]) -> dict[str, int]:
        """Delete artifact files from disk.

        Returns counts: {deleted, missing, errors}.
        """
        deleted = 0
        missing = 0
        errors = 0
        for a in artifacts:
            try:
                p = self._resolve_artifact_path(a.path)
                if p.exists():
                    p.unlink()
                    deleted += 1
                else:
                    missing += 1
            except Exception:
                errors += 1
        return {"deleted": deleted, "missing": missing, "errors": errors}
