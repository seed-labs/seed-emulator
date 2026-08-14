"""Strict normalized intent contracts produced from untrusted LLM output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Dict, Mapping, Optional, Tuple


INTENT_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
DIFFICULTIES = {"easy", "medium", "hard", "expert"}
FAULT_RELATIONSHIPS = {"single", "independent", "cascading"}


def canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _strict(value: Mapping[str, Any], fields: Tuple[str, ...]) -> Dict[str, Any]:
    data = dict(value)
    missing, extra = set(fields) - set(data), set(data) - set(fields)
    if missing or extra:
        raise ValueError(
            f"invalid BenchmarkIntent keys: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return data


@dataclass(frozen=True)
class BenchmarkIntent:
    """Canonical user intent; execution authority is deliberately absent."""

    request_id: str
    objective: str
    applications: Tuple[str, ...]
    seed: str
    difficulty: Optional[str]
    scale: int
    fault_types: Tuple[str, ...]
    fault_count: int
    fault_relationship: str
    topology_id: str
    observer_required: bool
    publish_requested: bool
    unknown_requirements: Tuple[str, ...]
    assumptions: Tuple[str, ...]
    source_text_sha256: str
    provider_model: str
    schema_version: int = INTENT_SCHEMA_VERSION

    @classmethod
    def from_provider_output(
        cls,
        value: Mapping[str, Any],
        *,
        source_text: str,
        seed: str,
        provider_model: str,
    ) -> "BenchmarkIntent":
        fields = (
            "schema_version", "objective", "applications", "difficulty", "scale",
            "fault_types", "fault_count", "fault_relationship", "topology_id",
            "observer_required", "publish_requested", "unknown_requirements",
            "assumptions",
        )
        data = _strict(value, fields)
        if int(data["schema_version"]) != INTENT_SCHEMA_VERSION:
            raise ValueError("unsupported BenchmarkIntent schema_version")
        text = " ".join(source_text.split())
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        identity = canonical_sha256(
            {"text": text, "seed": seed, "provider_model": provider_model}
        )
        applications = tuple(str(item) for item in data["applications"])
        fault_types = tuple(str(item) for item in data["fault_types"])
        unknown = tuple(str(item) for item in data["unknown_requirements"])
        assumptions = tuple(str(item) for item in data["assumptions"])
        difficulty = data["difficulty"]
        intent = cls(
            request_id=f"nl_{identity[:20]}",
            objective=str(data["objective"]).strip(),
            applications=applications,
            seed=str(seed).strip(),
            difficulty=None if difficulty is None else str(difficulty),
            scale=int(data["scale"]),
            fault_types=fault_types,
            fault_count=int(data["fault_count"]),
            fault_relationship=str(data["fault_relationship"]),
            topology_id=str(data["topology_id"] or ""),
            observer_required=bool(data["observer_required"]),
            publish_requested=bool(data["publish_requested"]),
            unknown_requirements=unknown,
            assumptions=assumptions,
            source_text_sha256=text_sha,
            provider_model=str(provider_model),
        )
        intent.validate()
        return intent

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BenchmarkIntent":
        fields = tuple(cls.__dataclass_fields__)
        data = _strict(value, fields)
        for key in ("applications", "fault_types", "unknown_requirements", "assumptions"):
            data[key] = tuple(str(item) for item in data[key])
        intent = cls(**data)
        intent.validate()
        return intent

    def validate(self) -> None:
        if self.schema_version != INTENT_SCHEMA_VERSION:
            raise ValueError("unsupported intent schema")
        if not ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("invalid intent request_id")
        if not self.objective or len(self.objective) > 2000:
            raise ValueError("intent objective is invalid")
        if not self.seed or len(self.seed) > 256:
            raise ValueError("intent seed is invalid")
        if len(self.applications) > 16 or len(set(self.applications)) != len(self.applications):
            raise ValueError("intent applications must be unique")
        if len(self.fault_types) > 64 or len(set(self.fault_types)) != len(self.fault_types):
            raise ValueError("intent fault types must be unique")
        if any(not ID_PATTERN.fullmatch(item) for item in self.applications + self.fault_types):
            raise ValueError("intent contains an invalid capability identity")
        if self.difficulty is not None and self.difficulty not in DIFFICULTIES:
            raise ValueError("intent difficulty is invalid")
        if not 1 <= self.scale <= 10000 or not 0 <= self.fault_count <= 64:
            raise ValueError("intent scale or fault count is out of range")
        if self.fault_relationship not in FAULT_RELATIONSHIPS:
            raise ValueError("intent fault relationship is invalid")
        if self.topology_id and not ID_PATTERN.fullmatch(self.topology_id):
            raise ValueError("intent topology_id is invalid")
        if any(not item or len(item) > 256 for item in self.unknown_requirements):
            raise ValueError("intent unknown requirement is invalid")
        if any(not item or len(item) > 512 for item in self.assumptions):
            raise ValueError("intent assumption is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_text_sha256):
            raise ValueError("intent source fingerprint is invalid")
        if not self.provider_model or len(self.provider_model) > 256:
            raise ValueError("intent provider model is invalid")

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ("applications", "fault_types", "unknown_requirements", "assumptions"):
            value[key] = list(value[key])
        return value

    @property
    def fingerprint(self) -> str:
        return canonical_sha256(self.to_dict())
