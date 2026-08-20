"""Strict natural-language contracts for arbitrary declarative benchmark scenes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Dict, Mapping, Tuple

from jsonschema import Draft202012Validator


SCENE_SCHEMA_VERSION = 1
IDENTITY = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
NODE = re.compile(r"^(?:router0|host(?:0|[1-9][0-9]{0,2}))$")
SYSTEM_CEILINGS = {
    "max_containers": 10000,
    "max_networks": 512,
    "max_memory_mb": 262144,
    "max_cpu_cores": 256.0,
    "max_ases": 128,
    "max_links": 256,
}


_budget_properties = {
    "max_containers": {"type": "integer", "minimum": 3, "maximum": 10000},
    "max_networks": {"type": "integer", "minimum": 1, "maximum": 512},
    "max_memory_mb": {"type": "integer", "minimum": 256, "maximum": 262144},
    "max_cpu_cores": {"type": "number", "exclusiveMinimum": 0, "maximum": 256},
    "max_ases": {"type": "integer", "minimum": 1, "maximum": 128},
    "max_links": {"type": "integer", "minimum": 0, "maximum": 256},
}


BENCHMARK_SCENE_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "BenchmarkSceneProviderOutputV1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "objective", "topology", "application_placements",
        "fault_types", "fault_count", "fault_relationship", "difficulty",
        "observer_required", "assumptions", "unknown_requirements",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "objective": {"type": "string", "minLength": 1, "maxLength": 2000},
        "topology": {
            "type": "object", "additionalProperties": False,
            "required": [
                "as_count", "hosts_per_as", "edge_policy", "extra_links",
                "explicit_edges", "asn_start", "lan_pool", "ix_pool",
                "loopback_pool", "lan_prefixlen", "ix_prefixlen", "platform",
                "budget",
            ],
            "properties": {
                "as_count": {"type": "integer", "minimum": 1, "maximum": 128},
                "hosts_per_as": {"type": "integer", "minimum": 1, "maximum": 200},
                "edge_policy": {"enum": ["tree", "ring", "mesh", "random_connected", "explicit"]},
                "extra_links": {"type": "integer", "minimum": 0, "maximum": 256},
                "explicit_edges": {
                    "type": "array", "maxItems": 256, "uniqueItems": True,
                    "items": {
                        "type": "array", "prefixItems": [
                            {"type": "integer", "minimum": 0, "maximum": 127},
                            {"type": "integer", "minimum": 0, "maximum": 127},
                        ], "items": False, "minItems": 2, "maxItems": 2,
                    },
                },
                "asn_start": {"type": "integer", "minimum": 1, "maximum": 4294967294},
                "lan_pool": {"type": "string", "minLength": 9, "maxLength": 32},
                "ix_pool": {"type": "string", "minLength": 9, "maxLength": 32},
                "loopback_pool": {"type": "string", "minLength": 9, "maxLength": 32},
                "lan_prefixlen": {"type": "integer", "minimum": 8, "maximum": 30},
                "ix_prefixlen": {"type": "integer", "minimum": 8, "maximum": 30},
                "platform": {"enum": ["amd", "arm"]},
                "budget": {
                    "type": "object", "additionalProperties": False,
                    "required": list(SYSTEM_CEILINGS),
                    "properties": _budget_properties,
                },
            },
        },
        "application_placements": {
            "type": "array", "maxItems": 16,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["template_id", "target_roles", "target_asns", "target_nodes"],
                "properties": {
                    "template_id": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,95}$"},
                    "target_roles": {
                        "type": "array", "minItems": 1, "maxItems": 2,
                        "uniqueItems": True, "items": {"enum": ["router", "host"]},
                    },
                    "target_asns": {
                        "type": "array", "maxItems": 128, "uniqueItems": True,
                        "items": {"type": "integer", "minimum": 1, "maximum": 4294967294},
                    },
                    "target_nodes": {
                        "type": "array", "maxItems": 201, "uniqueItems": True,
                        "items": {"type": "string", "pattern": "^(?:router0|host(?:0|[1-9][0-9]{0,2}))$"},
                    },
                },
            },
        },
        "fault_types": {
            "type": "array", "maxItems": 64, "uniqueItems": True,
            "items": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,95}$"},
        },
        "fault_count": {"type": "integer", "minimum": 0, "maximum": 64},
        "fault_relationship": {"enum": ["single", "independent", "cascading"]},
        "difficulty": {"enum": ["easy", "medium", "hard", "expert"]},
        "observer_required": {"type": "boolean"},
        "assumptions": {
            "type": "array", "maxItems": 32, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 512},
        },
        "unknown_requirements": {
            "type": "array", "maxItems": 32, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
        },
    },
}


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_scene_provider_output(value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(BENCHMARK_SCENE_OUTPUT_SCHEMA).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            {"path": "/".join(str(part) for part in error.absolute_path), "message": error.message}
            for error in errors
        ]
        raise ValueError(f"benchmark scene output failed JSON Schema: {details}")


@dataclass(frozen=True)
class SceneApplicationPlacement:
    template_id: str
    target_roles: Tuple[str, ...]
    target_asns: Tuple[int, ...]
    target_nodes: Tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SceneApplicationPlacement":
        expected = {"template_id", "target_roles", "target_asns", "target_nodes"}
        if set(value) != expected:
            raise ValueError("invalid scene application placement keys")
        placement = cls(
            str(value["template_id"]),
            tuple(str(item) for item in value["target_roles"]),
            tuple(int(item) for item in value["target_asns"]),
            tuple(str(item) for item in value["target_nodes"]),
        )
        if not IDENTITY.fullmatch(placement.template_id):
            raise ValueError("invalid scene application template identity")
        if not placement.target_roles or not set(placement.target_roles) <= {"router", "host"}:
            raise ValueError("invalid scene application target roles")
        if len(set(placement.target_roles)) != len(placement.target_roles):
            raise ValueError("duplicate scene application target role")
        if len(set(placement.target_asns)) != len(placement.target_asns):
            raise ValueError("duplicate scene application target ASN")
        if len(set(placement.target_nodes)) != len(placement.target_nodes) or any(
            not NODE.fullmatch(item) for item in placement.target_nodes
        ):
            raise ValueError("invalid scene application target node")
        return placement


@dataclass(frozen=True)
class BenchmarkSceneIntent:
    request_id: str
    topology_id: str
    objective: str
    topology: Dict[str, Any]
    application_placements: Tuple[SceneApplicationPlacement, ...]
    fault_types: Tuple[str, ...]
    fault_count: int
    fault_relationship: str
    difficulty: str
    observer_required: bool
    assumptions: Tuple[str, ...]
    unknown_requirements: Tuple[str, ...]
    seed: str
    source_text_sha256: str
    provider_model: str
    schema_version: int = SCENE_SCHEMA_VERSION

    @classmethod
    def from_provider_output(
        cls, value: Mapping[str, Any], *, source_text: str, seed: str, provider_model: str,
    ) -> "BenchmarkSceneIntent":
        validate_scene_provider_output(value)
        normalized = " ".join(source_text.split())
        identity = _sha({
            "text": normalized, "seed": seed, "provider_model": provider_model,
            "kind": "benchmark_scene_v1",
        })
        intent = cls(
            request_id=f"nlscene_req_{identity[:16]}",
            topology_id=f"nlscene_{identity[:16]}",
            objective=str(value["objective"]).strip(),
            topology=dict(value["topology"]),
            application_placements=tuple(
                SceneApplicationPlacement.from_dict(item)
                for item in value["application_placements"]
            ),
            fault_types=tuple(str(item) for item in value["fault_types"]),
            fault_count=int(value["fault_count"]),
            fault_relationship=str(value["fault_relationship"]),
            difficulty=str(value["difficulty"]),
            observer_required=bool(value["observer_required"]),
            assumptions=tuple(str(item) for item in value["assumptions"]),
            unknown_requirements=tuple(str(item) for item in value["unknown_requirements"]),
            seed=str(seed),
            source_text_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            provider_model=str(provider_model),
        )
        intent.validate()
        return intent

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BenchmarkSceneIntent":
        fields = set(cls.__dataclass_fields__)
        if set(value) != fields:
            raise ValueError("invalid normalized BenchmarkSceneIntent keys")
        data = dict(value)
        data["application_placements"] = tuple(
            SceneApplicationPlacement.from_dict(item)
            for item in data["application_placements"]
        )
        for key in ("fault_types", "assumptions", "unknown_requirements"):
            data[key] = tuple(str(item) for item in data[key])
        data["topology"] = dict(data["topology"])
        intent = cls(**data)
        intent.validate()
        return intent

    def validate(self) -> None:
        if self.schema_version != SCENE_SCHEMA_VERSION:
            raise ValueError("unsupported BenchmarkSceneIntent schema")
        if not IDENTITY.fullmatch(self.request_id) or not IDENTITY.fullmatch(self.topology_id):
            raise ValueError("invalid normalized scene identity")
        if not self.objective or not self.seed or not self.provider_model:
            raise ValueError("incomplete normalized scene metadata")
        if len(set(self.fault_types)) != len(self.fault_types):
            raise ValueError("scene fault types must be unique")
        if self.fault_count < 0 or self.fault_relationship not in {
            "single", "independent", "cascading",
        }:
            raise ValueError("invalid scene fault declaration")
        if self.difficulty not in {"easy", "medium", "hard", "expert"}:
            raise ValueError("invalid scene difficulty")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_text_sha256):
            raise ValueError("invalid scene source fingerprint")
        budget = self.topology.get("budget")
        if not isinstance(budget, Mapping) or set(budget) != set(SYSTEM_CEILINGS):
            raise ValueError("invalid scene resource budget")
        for field, ceiling in SYSTEM_CEILINGS.items():
            minimum = 0 if field == "max_links" else 0.000001
            if float(budget[field]) < minimum or float(budget[field]) > ceiling:
                raise ValueError(f"scene resource ceiling exceeded: {field}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "topology_id": self.topology_id,
            "objective": self.objective,
            "topology": self.topology,
            "application_placements": [asdict(item) for item in self.application_placements],
            "fault_types": list(self.fault_types),
            "fault_count": self.fault_count,
            "fault_relationship": self.fault_relationship,
            "difficulty": self.difficulty,
            "observer_required": self.observer_required,
            "assumptions": list(self.assumptions),
            "unknown_requirements": list(self.unknown_requirements),
            "seed": self.seed,
            "source_text_sha256": self.source_text_sha256,
            "provider_model": self.provider_model,
            "schema_version": self.schema_version,
        }

    @property
    def fingerprint(self) -> str:
        return _sha(self.to_dict())
