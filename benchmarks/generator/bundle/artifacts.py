"""Tamper-evident artifacts exchanged by benchmark-producing agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, Mapping, Tuple


ARTIFACT_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
ARTIFACT_TYPES = {
    "topology_ref", "software", "service", "workload", "fault_set",
    "test", "oracle", "scoring", "blind_policy", "lifecycle",
}


def canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class AgentArtifact:
    """One immutable, provenance-carrying output from a collaborating agent."""

    artifact_type: str
    artifact_id: str
    producer: str
    payload: Dict[str, Any]
    input_fingerprints: Tuple[str, ...] = ()
    capabilities_required: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    artifact_fingerprint: str = ""
    schema_version: int = ARTIFACT_SCHEMA_VERSION

    def unsigned_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value.pop("artifact_fingerprint")
        for field in (
            "input_fingerprints", "capabilities_required", "warnings"
        ):
            value[field] = list(value[field])
        return value

    def to_dict(self) -> Dict[str, Any]:
        value = self.unsigned_dict()
        value["artifact_fingerprint"] = self.artifact_fingerprint
        return value

    def signed(self) -> "AgentArtifact":
        validate_artifact(self, require_fingerprint=False)
        return AgentArtifact(
            **{
                **self.__dict__,
                "artifact_fingerprint": canonical_sha256(self.unsigned_dict()),
            }
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AgentArtifact":
        data = dict(value)
        if set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid AgentArtifact schema keys")
        for field in (
            "input_fingerprints", "capabilities_required", "warnings"
        ):
            data[field] = tuple(str(item) for item in data[field])
        data["payload"] = dict(data["payload"])
        artifact = cls(**data)
        validate_artifact(artifact, require_fingerprint=True)
        return artifact


def validate_artifact(
    artifact: AgentArtifact, *, require_fingerprint: bool = True
) -> None:
    if artifact.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("unsupported AgentArtifact schema_version")
    if artifact.artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"unsupported artifact_type={artifact.artifact_type}")
    for label, value in (
        ("artifact_id", artifact.artifact_id), ("producer", artifact.producer)
    ):
        if not ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid AgentArtifact {label}")
    if not isinstance(artifact.payload, dict):
        raise ValueError("AgentArtifact payload must be an object")
    for fingerprint in artifact.input_fingerprints:
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError("invalid AgentArtifact input fingerprint")
    if require_fingerprint:
        expected = canonical_sha256(artifact.unsigned_dict())
        if artifact.artifact_fingerprint != expected:
            raise ValueError("AgentArtifact fingerprint mismatch")


class ArtifactStore:
    """Atomic benchmark-local store; artifacts are immutable by default."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, artifact_id: str) -> Path:
        if not ID_PATTERN.fullmatch(artifact_id):
            raise ValueError("invalid artifact id")
        path = (self.root / f"{artifact_id}.json").resolve()
        path.relative_to(self.root)
        return path

    def write(self, artifact: AgentArtifact, *, force: bool = False) -> Path:
        signed = artifact.signed()
        path = self.path(signed.artifact_id)
        if path.exists() and not force:
            existing = self.load(signed.artifact_id)
            if existing == signed:
                return path
            raise FileExistsError(f"artifact already exists: {signed.artifact_id}")
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=self.root, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    signed.to_dict(), handle, ensure_ascii=False,
                    indent=2, sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        return path

    def load(self, artifact_id: str) -> AgentArtifact:
        return AgentArtifact.from_dict(
            json.loads(self.path(artifact_id).read_text(encoding="utf-8"))
        )

    def inventory(self) -> Tuple[AgentArtifact, ...]:
        return tuple(
            AgentArtifact.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.root.glob("*.json"))
        )
