"""Top-level immutable BenchmarkBundle contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Dict, Mapping, Tuple


BUNDLE_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


def canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class BenchmarkBundleSpec:
    benchmark_id: str
    seed: str
    artifact_ids: Tuple[str, ...]
    enabled: bool = False
    schema_version: int = BUNDLE_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BenchmarkBundleSpec":
        data = dict(value)
        required = {"schema_version", "benchmark_id", "seed", "artifact_ids"}
        optional = {"enabled"}
        if set(data) - required - optional or required - set(data):
            raise ValueError("invalid BenchmarkBundleSpec schema keys")
        if data["schema_version"] != BUNDLE_SCHEMA_VERSION:
            raise ValueError("unsupported BenchmarkBundleSpec version")
        benchmark_id = str(data["benchmark_id"])
        artifacts = tuple(str(item) for item in data["artifact_ids"])
        if not ID_PATTERN.fullmatch(benchmark_id) or not str(data["seed"]):
            raise ValueError("invalid benchmark identity")
        if not artifacts or len(artifacts) != len(set(artifacts)):
            raise ValueError("bundle artifacts must be non-empty and unique")
        if any(not ID_PATTERN.fullmatch(item) for item in artifacts):
            raise ValueError("bundle contains invalid artifact id")
        return cls(
            benchmark_id=benchmark_id, seed=str(data["seed"]),
            artifact_ids=artifacts, enabled=bool(data.get("enabled", False)),
        )

    def to_dict(self):
        value = asdict(self)
        value["artifact_ids"] = list(self.artifact_ids)
        return value


@dataclass(frozen=True)
class CompiledBenchmarkBundle:
    benchmark_id: str
    seed: str
    topology_id: str
    topology_fingerprint: str
    generator_contract_sha256: str
    artifact_fingerprints: Tuple[str, ...]
    public_bundle: Dict[str, Any]
    private_bundle: Dict[str, Any]
    safety_review: Dict[str, Any]
    bundle_fingerprint: str
    schema_version: int = BUNDLE_SCHEMA_VERSION

    def unsigned_dict(self):
        value = asdict(self)
        value.pop("bundle_fingerprint")
        value["artifact_fingerprints"] = list(self.artifact_fingerprints)
        return value

    def to_dict(self):
        value = self.unsigned_dict()
        value["bundle_fingerprint"] = self.bundle_fingerprint
        return value

    @classmethod
    def build(cls, **kwargs) -> "CompiledBenchmarkBundle":
        provisional = cls(bundle_fingerprint="", **kwargs)
        return cls(
            **{**provisional.__dict__, "bundle_fingerprint": canonical_sha256(provisional.unsigned_dict())}
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompiledBenchmarkBundle":
        data = dict(value)
        if set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid compiled bundle schema")
        data["artifact_fingerprints"] = tuple(data["artifact_fingerprints"])
        bundle = cls(**data)
        if bundle.schema_version != BUNDLE_SCHEMA_VERSION:
            raise ValueError("unsupported compiled bundle schema")
        if canonical_sha256(bundle.unsigned_dict()) != bundle.bundle_fingerprint:
            raise ValueError("compiled bundle fingerprint mismatch")
        return bundle
