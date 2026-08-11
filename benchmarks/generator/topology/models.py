"""Strict declarative models for generated SEED Emulator topologies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple


TOPOLOGY_SCHEMA_VERSION = 1
TOPOLOGY_GENERATOR_VERSION = "1.0.0"


def _strict(value: Mapping[str, Any], required, optional=()) -> Dict[str, Any]:
    data = dict(value)
    missing = sorted(set(required) - set(data))
    extra = sorted(set(data) - set(required) - set(optional))
    if missing or extra:
        raise ValueError(f"invalid topology schema keys: missing={missing}, extra={extra}")
    return data


@dataclass(frozen=True)
class ResourceBudget:
    max_containers: int = 256
    max_networks: int = 256
    max_memory_mb: int = 32768
    max_cpu_cores: float = 16.0
    max_ases: int = 128
    max_links: int = 256

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceBudget":
        fields = tuple(cls.__dataclass_fields__)
        data = _strict(value, (), fields)
        return cls(**data)


@dataclass(frozen=True)
class TopologyRequest:
    topology_id: str
    master_seed: str
    as_count: int
    hosts_per_as: int
    edge_policy: str = "ring"
    extra_links: int = 0
    explicit_edges: Tuple[Tuple[int, int], ...] = ()
    asn_start: int = 64512
    lan_pool: str = "10.0.0.0/8"
    ix_pool: str = "172.16.0.0/12"
    loopback_pool: str = "100.64.0.0/10"
    lan_prefixlen: int = 24
    ix_prefixlen: int = 29
    platform: str = "amd"
    budget: ResourceBudget = ResourceBudget()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TopologyRequest":
        required = ("topology_id", "master_seed", "as_count", "hosts_per_as")
        optional = tuple(item for item in cls.__dataclass_fields__ if item not in required)
        data = _strict(value, required, optional)
        if "budget" in data:
            data["budget"] = ResourceBudget.from_dict(data["budget"])
        data["explicit_edges"] = tuple(
            tuple(int(endpoint) for endpoint in edge)
            for edge in data.get("explicit_edges", ())
        )
        return cls(**data)

    @classmethod
    def from_json_file(cls, path: Path) -> "TopologyRequest":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class AutonomousSystemPlan:
    index: int
    asn: int
    lan_prefix: str
    router_address: str
    loopback_address: str
    host_addresses: Tuple[str, ...]


@dataclass(frozen=True)
class ExternalLinkPlan:
    index: int
    ix_id: int
    left_asn: int
    right_asn: int
    prefix: str
    left_address: str
    right_address: str


@dataclass(frozen=True)
class ResourceEstimate:
    containers: int
    networks: int
    memory_mb: int
    cpu_cores: float
    ases: int
    links: int


@dataclass(frozen=True)
class TopologyPlan:
    topology_id: str
    topology_name: str
    master_seed: str
    edge_policy: str
    platform: str
    request: Dict[str, Any]
    autonomous_systems: Tuple[AutonomousSystemPlan, ...]
    external_links: Tuple[ExternalLinkPlan, ...]
    resource_estimate: ResourceEstimate
    fingerprint: str
    schema_version: int = TOPOLOGY_SCHEMA_VERSION
    generator_version: str = TOPOLOGY_GENERATOR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TopologyPlan":
        fields = tuple(cls.__dataclass_fields__)
        data = _strict(value, fields)
        if data["schema_version"] != TOPOLOGY_SCHEMA_VERSION:
            raise ValueError("unsupported topology schema version")
        if data["generator_version"] != TOPOLOGY_GENERATOR_VERSION:
            raise ValueError("unsupported topology generator version")
        data["autonomous_systems"] = tuple(
            AutonomousSystemPlan(
                **{**item, "host_addresses": tuple(item["host_addresses"])}
            )
            for item in data["autonomous_systems"]
        )
        data["external_links"] = tuple(
            ExternalLinkPlan(**item) for item in data["external_links"]
        )
        data["resource_estimate"] = ResourceEstimate(**data["resource_estimate"])
        request = TopologyRequest.from_dict(data["request"])
        data["request"] = {
            **{key: value for key, value in request.__dict__.items() if key != "budget"},
            "budget": request.budget.__dict__,
        }
        return cls(**data)
