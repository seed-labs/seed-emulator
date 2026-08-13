"""FaultSpec v1 and immutable compiled execution-plan contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Dict, Mapping, Tuple


FAULT_SPEC_VERSION = 1


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _mapping(value: object, field: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return dict(value)


@dataclass(frozen=True)
class FaultSpec:
    """Backend-neutral fault declaration resolved against capabilities."""

    fault_id: str
    fault_type: str
    selector: Dict[str, Any]
    parameters: Dict[str, Any]
    expectations: Dict[str, Any]
    safety: Dict[str, Any]
    seed: str
    schedule: Dict[str, Any]
    depends_on: Tuple[str, ...] = ()
    schema_version: int = FAULT_SPEC_VERSION

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["depends_on"] = list(self.depends_on)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FaultSpec":
        data = dict(value)
        required = {
            "schema_version", "fault_id", "fault_type", "selector",
            "parameters", "expectations", "safety", "seed", "schedule",
        }
        optional = {"depends_on"}
        missing = required - set(data)
        extra = set(data) - required - optional
        if missing or extra:
            raise ValueError(
                f"invalid FaultSpec keys: missing={sorted(missing)}, "
                f"extra={sorted(extra)}"
            )
        if data["schema_version"] != FAULT_SPEC_VERSION:
            raise ValueError("unsupported FaultSpec schema_version")
        fault_id = str(data["fault_id"])
        fault_type = str(data["fault_type"])
        if not fault_id or not fault_type:
            raise ValueError("fault_id and fault_type must not be empty")
        return cls(
            fault_id=fault_id,
            fault_type=fault_type,
            selector=_mapping(data["selector"], "selector"),
            parameters=_mapping(data["parameters"], "parameters"),
            expectations=_mapping(data["expectations"], "expectations"),
            safety=_mapping(data["safety"], "safety"),
            seed=str(data["seed"]),
            schedule=_mapping(data["schedule"], "schedule"),
            depends_on=tuple(data.get("depends_on", ())),
        )


@dataclass(frozen=True)
class FaultAction:
    """One auditable and independently recoverable mutation."""

    action_id: str
    driver: str
    category: str
    targets: Tuple[str, ...]
    artifact: str
    faulty_value: str
    expected_value: str
    resource_locks: Tuple[str, ...]
    inject_command: str
    active_check_command: str
    active_verifier_kind: str
    active_verifier_value: str
    snapshot_command: str
    cleanup_command: str
    at_seconds: float = 0.0
    duration_seconds: float = 0.0
    inject_order: int = 0
    cleanup_order: int = 0
    depends_on: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ("targets", "resource_locks", "depends_on"):
            value[key] = list(value[key])
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FaultAction":
        data = dict(value)
        if set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid compiled fault action schema")
        for key in ("targets", "resource_locks", "depends_on"):
            data[key] = tuple(data[key])
        return cls(**data)


@dataclass(frozen=True)
class CompiledFaultPlan:
    """Deterministic execution boundary produced by the fault compiler."""

    fault_ids: Tuple[str, ...]
    topology_fingerprint: str
    actions: Tuple[FaultAction, ...]
    affected_assets: Tuple[str, ...]
    affected_asns: Tuple[int, ...]
    relationship: str
    plan_fingerprint: str
    impact: Dict[str, Any]

    def unsigned_dict(self) -> Dict[str, Any]:
        return {
            "fault_ids": list(self.fault_ids),
            "topology_fingerprint": self.topology_fingerprint,
            "actions": [item.to_dict() for item in self.actions],
            "affected_assets": list(self.affected_assets),
            "affected_asns": list(self.affected_asns),
            "relationship": self.relationship,
            "impact": self.impact,
        }

    def to_dict(self) -> Dict[str, Any]:
        value = self.unsigned_dict()
        value["plan_fingerprint"] = self.plan_fingerprint
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompiledFaultPlan":
        data = dict(value)
        if set(data) != set(cls.__dataclass_fields__):
            raise ValueError("invalid compiled fault plan schema")
        plan = cls(
            fault_ids=tuple(data["fault_ids"]),
            topology_fingerprint=str(data["topology_fingerprint"]),
            actions=tuple(FaultAction.from_dict(x) for x in data["actions"]),
            affected_assets=tuple(data["affected_assets"]),
            affected_asns=tuple(int(x) for x in data["affected_asns"]),
            relationship=str(data["relationship"]),
            plan_fingerprint=str(data["plan_fingerprint"]),
            impact=dict(data["impact"]),
        )
        if canonical_sha256(plan.unsigned_dict()) != plan.plan_fingerprint:
            raise ValueError("compiled fault plan fingerprint mismatch")
        return plan
