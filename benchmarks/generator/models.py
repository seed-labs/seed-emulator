"""Strict data models used by the benchmark generator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping, Tuple


SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
VALID_TRACKS = {
    "network_functional",
    "network_control_plane",
    "config_lint",
    "advanced",
    "robustness",
}
VALID_DIFFICULTIES = {"basic", "core", "advanced"}


def scenario_fingerprint(
    template_id: str,
    topology: str,
    parameters: Mapping[str, Any],
) -> str:
    payload = json.dumps(
        {
            "template_id": template_id,
            "topology": topology,
            "parameters": dict(parameters),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _strict_mapping(
    value: Mapping[str, Any],
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> Dict[str, Any]:
    data = dict(value)
    required_keys = set(required)
    allowed_keys = required_keys | set(optional)
    missing = sorted(required_keys - set(data))
    extra = sorted(set(data) - allowed_keys)
    if missing or extra:
        raise ValueError(
            f"invalid schema keys: missing={missing}, extra={extra}"
        )
    return data


@dataclass(frozen=True)
class GenerationJob:
    """One deterministic suite-generation request."""

    suite_id: str
    case_count: int = 20
    master_seed: str = "0"
    template_ids: Tuple[str, ...] = ()
    topology: str = ""
    benchmark_track: str = "robustness"
    enabled: bool = True


@dataclass(frozen=True)
class ScenarioSpec:
    """Declarative representation compiled into the existing scenario API."""

    name: str
    description: str
    topology: str
    fault_type: str
    template_id: str
    parameters: Dict[str, Any]
    diagnosis_targets: Tuple[str, ...]
    diagnosis_artifact: str
    diagnosis_faulty_value: str
    diagnosis_expected_value: str
    benchmark_track: str
    difficulty: str
    main_score_eligible: bool
    quarantine_reason: str
    repair_containers: Tuple[str, ...]
    scenario_seed: int
    fingerprint: str
    convergence_timeout: int = 90
    fault_settle_seconds: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScenarioSpec":
        fields = tuple(cls.__dataclass_fields__)
        data = _strict_mapping(value, fields)
        data["diagnosis_targets"] = tuple(data["diagnosis_targets"])
        data["repair_containers"] = tuple(data["repair_containers"])
        data["parameters"] = dict(data["parameters"])
        return cls(**data)


@dataclass(frozen=True)
class SuiteManifest:
    """A reproducible generated suite and its contract provenance."""

    suite_id: str
    master_seed: str
    contract_sha256: str
    scenarios: Tuple[ScenarioSpec, ...]
    enabled: bool = True
    schema_version: int = SCHEMA_VERSION
    generator_version: str = GENERATOR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "suite_id": self.suite_id,
            "master_seed": self.master_seed,
            "contract_sha256": self.contract_sha256,
            "enabled": self.enabled,
            "scenarios": [item.to_dict() for item in self.scenarios],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SuiteManifest":
        data = _strict_mapping(
            value,
            (
                "schema_version",
                "generator_version",
                "suite_id",
                "master_seed",
                "contract_sha256",
                "enabled",
                "scenarios",
            ),
        )
        if data["schema_version"] != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version={data['schema_version']}"
            )
        scenarios = tuple(
            ScenarioSpec.from_dict(item) for item in data["scenarios"]
        )
        return cls(
            suite_id=data["suite_id"],
            master_seed=str(data["master_seed"]),
            contract_sha256=data["contract_sha256"],
            scenarios=scenarios,
            enabled=bool(data["enabled"]),
            schema_version=data["schema_version"],
            generator_version=data["generator_version"],
        )
