"""Strict application, workload, test and scoring contracts for bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, Mapping, Tuple


SPEC_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
PHASES = {"baseline", "active", "repair", "recovery"}


def _strict(
    value: Mapping[str, Any], required, optional=()
) -> Dict[str, Any]:
    data = dict(value)
    missing = set(required) - set(data)
    extra = set(data) - set(required) - set(optional)
    if missing or extra:
        raise ValueError(
            f"invalid schema keys: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return data


def _identity(value: str, label: str) -> str:
    text = str(value)
    if not ID_PATTERN.fullmatch(text):
        raise ValueError(f"invalid {label}")
    return text


def _selector(value: object) -> Dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError("asset selector must be a non-empty object")
    selector = dict(value)
    allowed = {"container", "role", "asn", "software", "capability", "choose"}
    if set(selector) - allowed:
        raise ValueError("asset selector contains unsupported keys")
    choose = int(selector.get("choose", 1))
    if not 1 <= choose <= 64:
        raise ValueError("selector choose must be between 1 and 64")
    selector["choose"] = choose
    return selector


@dataclass(frozen=True)
class ServiceSpec:
    service_id: str
    driver: str
    selector: Dict[str, Any]
    capabilities_required: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    ports: Tuple[int, ...] = ()
    environment: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ServiceSpec":
        data = _strict(
            value, ("service_id", "driver", "selector"),
            ("capabilities_required", "dependencies", "ports", "environment",
             "parameters", "schema_version"),
        )
        if int(data.get("schema_version", 1)) != SPEC_VERSION:
            raise ValueError("unsupported ServiceSpec version")
        ports = tuple(int(item) for item in data.get("ports", ()))
        if len(set(ports)) != len(ports) or any(not 1 <= item <= 65535 for item in ports):
            raise ValueError("invalid ServiceSpec ports")
        return cls(
            service_id=_identity(data["service_id"], "service_id"),
            driver=_identity(data["driver"], "service driver"),
            selector=_selector(data["selector"]),
            capabilities_required=tuple(str(x) for x in data.get("capabilities_required", ())),
            dependencies=tuple(_identity(x, "service dependency") for x in data.get("dependencies", ())),
            ports=ports,
            environment={str(k): str(v) for k, v in dict(data.get("environment", {})).items()},
            parameters=dict(data.get("parameters", {})),
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class WorkloadSpec:
    workload_id: str
    driver: str
    source: Dict[str, Any]
    target_service: str
    parameters: Dict[str, Any]
    warmup_seconds: float = 0.0
    duration_seconds: float = 1.0
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkloadSpec":
        data = _strict(
            value, ("workload_id", "driver", "source", "target_service", "parameters"),
            ("warmup_seconds", "duration_seconds", "schema_version"),
        )
        warmup = float(data.get("warmup_seconds", 0))
        duration = float(data.get("duration_seconds", 1))
        if warmup < 0 or not 0 < duration <= 3600:
            raise ValueError("invalid workload timing")
        return cls(
            workload_id=_identity(data["workload_id"], "workload_id"),
            driver=_identity(data["driver"], "workload driver"),
            source=_selector(data["source"]),
            target_service=_identity(data["target_service"], "target_service"),
            parameters=dict(data["parameters"]),
            warmup_seconds=warmup, duration_seconds=duration,
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class TestSpec:
    test_id: str
    phase: str
    driver: str
    selector: Dict[str, Any]
    parameters: Dict[str, Any]
    assertion: Dict[str, Any]
    expectation_id: str
    samples: int = 1
    timeout_seconds: float = 10.0
    retries: int = 0
    public: bool = True
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TestSpec":
        data = _strict(
            value,
            ("test_id", "phase", "driver", "selector", "parameters",
             "assertion", "expectation_id"),
            ("samples", "timeout_seconds", "retries", "public", "schema_version"),
        )
        phase = str(data["phase"])
        if phase not in PHASES:
            raise ValueError("invalid test phase")
        samples, retries = int(data.get("samples", 1)), int(data.get("retries", 0))
        timeout = float(data.get("timeout_seconds", 10))
        if not 1 <= samples <= 100 or not 0 <= retries <= 10 or not 0 < timeout <= 300:
            raise ValueError("invalid test execution budget")
        assertion = dict(data["assertion"])
        if set(assertion) != {"kind", "value"}:
            raise ValueError("test assertion requires kind and value")
        return cls(
            test_id=_identity(data["test_id"], "test_id"), phase=phase,
            driver=_identity(data["driver"], "probe driver"),
            selector=_selector(data["selector"]), parameters=dict(data["parameters"]),
            assertion=assertion,
            expectation_id=_identity(data["expectation_id"], "expectation_id"),
            samples=samples, timeout_seconds=timeout, retries=retries,
            public=bool(data.get("public", True)),
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class OracleSpec:
    oracle_id: str
    required_tests: Tuple[str, ...]
    phase_requirements: Dict[str, Tuple[str, ...]]
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OracleSpec":
        data = _strict(
            value, ("oracle_id", "required_tests", "phase_requirements"),
            ("schema_version",),
        )
        requirements = {
            str(phase): tuple(_identity(x, "oracle test") for x in tests)
            for phase, tests in dict(data["phase_requirements"]).items()
        }
        if not requirements or set(requirements) - PHASES:
            raise ValueError("invalid OracleSpec phase requirements")
        required = tuple(_identity(x, "oracle required test") for x in data["required_tests"])
        if not required:
            raise ValueError("OracleSpec requires tests")
        return cls(
            oracle_id=_identity(data["oracle_id"], "oracle_id"),
            required_tests=required, phase_requirements=requirements,
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ScoringSpec:
    scoring_id: str
    weights: Dict[str, float]
    pass_threshold: float = 1.0
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScoringSpec":
        data = _strict(value, ("scoring_id", "weights"), ("pass_threshold", "schema_version"))
        weights = {str(k): float(v) for k, v in dict(data["weights"]).items()}
        threshold = float(data.get("pass_threshold", 1))
        if not weights or any(v <= 0 for v in weights.values()) or not 0 <= threshold <= 1:
            raise ValueError("invalid scoring weights or threshold")
        return cls(_identity(data["scoring_id"], "scoring_id"), weights, threshold)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class LifecycleSpec:
    baseline_timeout: int = 120
    fault_timeout: int = 60
    recovery_timeout: int = 180
    repeat_runs: int = 2
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LifecycleSpec":
        data = _strict(
            value, (), ("baseline_timeout", "fault_timeout", "recovery_timeout",
                        "repeat_runs", "schema_version"),
        )
        result = cls(**{key: int(item) for key, item in data.items() if key != "schema_version"})
        if not 1 <= result.baseline_timeout <= 3600 or not 1 <= result.fault_timeout <= 3600:
            raise ValueError("invalid lifecycle timeout")
        if not 1 <= result.recovery_timeout <= 3600 or not 1 <= result.repeat_runs <= 20:
            raise ValueError("invalid lifecycle recovery/repeat budget")
        return result

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class BlindPolicy:
    public_sections: Tuple[str, ...] = ("services", "workloads", "public_tests")
    private_sections: Tuple[str, ...] = ("fault_plans", "oracles", "scoring")
    forbidden_public_fields: Tuple[str, ...] = (
        "fault_id", "fault_type", "faulty_value", "expected_value",
        "inject_command", "cleanup_command", "root_causes",
    )
    schema_version: int = SPEC_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BlindPolicy":
        data = _strict(
            value, (), ("public_sections", "private_sections",
                        "forbidden_public_fields", "schema_version"),
        )
        kwargs = {
            key: tuple(str(x) for x in item)
            for key, item in data.items() if key != "schema_version"
        }
        policy = cls(**kwargs)
        if set(policy.public_sections) & set(policy.private_sections):
            raise ValueError("blind public and private sections overlap")
        return policy

    def to_dict(self):
        return asdict(self)
