"""Strict contracts for explicitly approved, container-scoped arbitrary scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Dict, Mapping, Tuple

from jsonschema import Draft202012Validator


UNSAFE_SCHEMA_VERSION = 1
IDENTITY = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
PHASES = {"baseline", "exercise", "verify"}
SYSTEM_LIMITS = {
    "max_services": 32,
    "max_cpu_cores": 16.0,
    "max_memory_mb": 32768,
    "max_disk_mb": 16384,
    "max_build_seconds": 1800,
    "max_runtime_seconds": 1800,
    "max_step_seconds": 300,
}


UNSAFE_PLAN_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "UnsafeScenarioProviderOutputV1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "unsafe_generated", "objective", "compose_yaml",
        "files", "steps", "budget", "assumptions",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "unsafe_generated": {"const": True},
        "objective": {"type": "string", "minLength": 1, "maxLength": 2000},
        "compose_yaml": {"type": "string", "minLength": 1, "maxLength": 262144},
        "files": {
            "type": "array", "minItems": 1, "maxItems": 64,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["path", "content", "mode"],
                "properties": {
                    "path": {"type": "string", "minLength": 1, "maxLength": 240},
                    "content": {"type": "string", "maxLength": 262144},
                    "mode": {"enum": ["0644", "0755"]},
                },
            },
        },
        "steps": {
            "type": "array", "minItems": 1, "maxItems": 128,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "step_id", "phase", "service", "shell",
                    "timeout_seconds", "expected_exit_code",
                ],
                "properties": {
                    "step_id": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,63}$"},
                    "phase": {"enum": ["baseline", "exercise", "verify"]},
                    "service": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,63}$"},
                    "shell": {"type": "string", "minLength": 1, "maxLength": 16384},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300},
                    "expected_exit_code": {"type": "integer", "minimum": 0, "maximum": 255},
                },
            },
        },
        "budget": {
            "type": "object", "additionalProperties": False,
            "required": list(SYSTEM_LIMITS),
            "properties": {
                "max_services": {"type": "integer", "minimum": 1, "maximum": 32},
                "max_cpu_cores": {"type": "number", "exclusiveMinimum": 0, "maximum": 16},
                "max_memory_mb": {"type": "integer", "minimum": 64, "maximum": 32768},
                "max_disk_mb": {"type": "integer", "minimum": 16, "maximum": 16384},
                "max_build_seconds": {"type": "integer", "minimum": 1, "maximum": 1800},
                "max_runtime_seconds": {"type": "integer", "minimum": 1, "maximum": 1800},
                "max_step_seconds": {"type": "integer", "minimum": 1, "maximum": 300},
            },
        },
        "assumptions": {
            "type": "array", "maxItems": 32, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 512},
        },
    },
}


def _canonical_sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _strict(value: Mapping[str, Any], fields: Tuple[str, ...], name: str) -> Dict[str, Any]:
    data = dict(value)
    missing, extra = set(fields) - set(data), set(data) - set(fields)
    if missing or extra:
        raise ValueError(f"invalid {name} keys: missing={sorted(missing)}, extra={sorted(extra)}")
    return data


def validate_unsafe_provider_output(value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(UNSAFE_PLAN_OUTPUT_SCHEMA).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            {"path": "/".join(str(part) for part in error.absolute_path), "message": error.message}
            for error in errors
        ]
        raise ValueError(f"unsafe LLM structured output failed JSON Schema: {details}")


@dataclass(frozen=True)
class UnsafeBudget:
    max_services: int
    max_cpu_cores: float
    max_memory_mb: int
    max_disk_mb: int
    max_build_seconds: int
    max_runtime_seconds: int
    max_step_seconds: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnsafeBudget":
        data = _strict(value, tuple(SYSTEM_LIMITS), "UnsafeBudget")
        budget = cls(
            max_services=int(data["max_services"]),
            max_cpu_cores=float(data["max_cpu_cores"]),
            max_memory_mb=int(data["max_memory_mb"]),
            max_disk_mb=int(data["max_disk_mb"]),
            max_build_seconds=int(data["max_build_seconds"]),
            max_runtime_seconds=int(data["max_runtime_seconds"]),
            max_step_seconds=int(data["max_step_seconds"]),
        )
        for field, ceiling in SYSTEM_LIMITS.items():
            value = getattr(budget, field)
            if value <= 0 or value > ceiling:
                raise ValueError(f"unsafe budget exceeds system ceiling: {field}")
        if budget.max_memory_mb < budget.max_services * 64:
            raise ValueError("unsafe budget must reserve at least 64 MiB per service")
        if budget.max_disk_mb < budget.max_services * 16:
            raise ValueError("unsafe budget must reserve at least 16 MiB per service")
        return budget


@dataclass(frozen=True)
class UnsafeFile:
    path: str
    content: str
    mode: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnsafeFile":
        data = _strict(value, ("path", "content", "mode"), "UnsafeFile")
        return cls(str(data["path"]), str(data["content"]), str(data["mode"]))


@dataclass(frozen=True)
class UnsafeStep:
    step_id: str
    phase: str
    service: str
    shell: str
    timeout_seconds: int
    expected_exit_code: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnsafeStep":
        fields = ("step_id", "phase", "service", "shell", "timeout_seconds", "expected_exit_code")
        data = _strict(value, fields, "UnsafeStep")
        step = cls(
            step_id=str(data["step_id"]), phase=str(data["phase"]),
            service=str(data["service"]), shell=str(data["shell"]),
            timeout_seconds=int(data["timeout_seconds"]),
            expected_exit_code=int(data["expected_exit_code"]),
        )
        if not IDENTITY.fullmatch(step.step_id) or not IDENTITY.fullmatch(step.service):
            raise ValueError("unsafe step identity is invalid")
        if step.phase not in PHASES or not step.shell.strip():
            raise ValueError("unsafe step phase or shell is invalid")
        return step


@dataclass(frozen=True)
class UnsafeScenarioPlan:
    request_id: str
    objective: str
    compose_yaml: str
    files: Tuple[UnsafeFile, ...]
    steps: Tuple[UnsafeStep, ...]
    budget: UnsafeBudget
    assumptions: Tuple[str, ...]
    source_text_sha256: str
    provider_model: str
    seed: str
    unsafe_generated: bool = True
    schema_version: int = UNSAFE_SCHEMA_VERSION

    @classmethod
    def from_provider_output(
        cls, value: Mapping[str, Any], *, source_text: str, seed: str, provider_model: str,
    ) -> "UnsafeScenarioPlan":
        validate_unsafe_provider_output(value)
        normalized_text = " ".join(source_text.split())
        identity = _canonical_sha({
            "text": normalized_text, "seed": seed, "provider_model": provider_model,
            "kind": "unsafe_scenario_v1",
        })
        plan = cls(
            request_id=f"unsafe_{identity[:20]}",
            objective=str(value["objective"]).strip(),
            compose_yaml=str(value["compose_yaml"]),
            files=tuple(UnsafeFile.from_dict(item) for item in value["files"]),
            steps=tuple(UnsafeStep.from_dict(item) for item in value["steps"]),
            budget=UnsafeBudget.from_dict(value["budget"]),
            assumptions=tuple(str(item) for item in value["assumptions"]),
            source_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            provider_model=provider_model,
            seed=seed,
        )
        plan.validate()
        return plan

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnsafeScenarioPlan":
        fields = tuple(cls.__dataclass_fields__)
        data = _strict(value, fields, "UnsafeScenarioPlan")
        data["files"] = tuple(UnsafeFile.from_dict(item) for item in data["files"])
        data["steps"] = tuple(UnsafeStep.from_dict(item) for item in data["steps"])
        data["budget"] = UnsafeBudget.from_dict(data["budget"])
        data["assumptions"] = tuple(str(item) for item in data["assumptions"])
        plan = cls(**data)
        plan.validate()
        return plan

    def validate(self) -> None:
        if self.schema_version != UNSAFE_SCHEMA_VERSION or self.unsafe_generated is not True:
            raise ValueError("unsafe plan marker or schema version is invalid")
        if not IDENTITY.fullmatch(self.request_id):
            raise ValueError("unsafe request identity is invalid")
        if not self.objective or not self.seed or not self.provider_model:
            raise ValueError("unsafe plan metadata is incomplete")
        if len({item.path for item in self.files}) != len(self.files):
            raise ValueError("unsafe generated file paths must be unique")
        if len({item.step_id for item in self.steps}) != len(self.steps):
            raise ValueError("unsafe step identities must be unique")
        if any(item.timeout_seconds > self.budget.max_step_seconds for item in self.steps):
            raise ValueError("unsafe step exceeds plan timeout budget")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_text_sha256):
            raise ValueError("unsafe source fingerprint is invalid")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "objective": self.objective,
            "compose_yaml": self.compose_yaml,
            "files": [asdict(item) for item in self.files],
            "steps": [asdict(item) for item in self.steps],
            "budget": asdict(self.budget),
            "assumptions": list(self.assumptions),
            "source_text_sha256": self.source_text_sha256,
            "provider_model": self.provider_model,
            "seed": self.seed,
            "unsafe_generated": self.unsafe_generated,
            "schema_version": self.schema_version,
        }

    @property
    def fingerprint(self) -> str:
        return _canonical_sha(self.to_dict())
