"""High-level production request compiled into a deterministic Agent DAG."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Dict, Mapping, Tuple

from generator.bundle.coordinator import AgentTask
from generator.bundle.models import BenchmarkBundleSpec


REQUEST_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
DIFFICULTIES = {"easy", "medium", "hard", "expert"}
RESOURCE_CLASSES = {"small", "medium", "large", "xlarge"}


def _strict(value: Mapping[str, Any], required, optional=()) -> Dict[str, Any]:
    data = dict(value)
    missing = set(required) - set(data)
    extra = set(data) - set(required) - set(optional)
    if missing or extra:
        raise ValueError(
            f"invalid BenchmarkRequest keys: missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )
    return data


@dataclass(frozen=True)
class BenchmarkRequest:
    """One auditable user intent; it never contains executable code."""

    request_id: str
    objective: str
    topology_id: str
    applications: Tuple[str, ...]
    seed: str
    difficulty: str = "medium"
    scale: int = 5
    fault_count: int = 1
    fault_types: Tuple[str, ...] = ()
    observer_template: str = "network_observer"
    topology_spec: str = ""
    prepare_topology: bool = False
    execute_lifecycle: bool = False
    qualification_runs: int = 2
    publish: bool = False
    resource_class: str = "small"
    schema_version: int = REQUEST_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BenchmarkRequest":
        required = (
            "schema_version", "request_id", "objective", "topology_id",
            "applications", "seed",
        )
        optional = tuple(
            key for key in cls.__dataclass_fields__ if key not in required
        )
        data = _strict(value, required, optional)
        if int(data["schema_version"]) != REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported BenchmarkRequest schema_version")
        request_id, topology_id = str(data["request_id"]), str(data["topology_id"])
        applications = tuple(str(item) for item in data["applications"])
        objective, seed = str(data["objective"]).strip(), str(data["seed"]).strip()
        difficulty = str(data.get("difficulty", "medium"))
        resource_class = str(data.get("resource_class", "small"))
        scale, fault_count = int(data.get("scale", 5)), int(data.get("fault_count", 1))
        qualification_runs = int(data.get("qualification_runs", 2))
        topology_spec = str(data.get("topology_spec", ""))
        if not ID_PATTERN.fullmatch(request_id) or not ID_PATTERN.fullmatch(topology_id):
            raise ValueError("invalid request or topology identity")
        if not objective or len(objective) > 1000 or not seed or len(seed) > 256:
            raise ValueError("request objective or seed is invalid")
        if not applications or len(applications) > 16 or len(set(applications)) != len(applications):
            raise ValueError("request requires 1-16 unique applications")
        if any(not ID_PATTERN.fullmatch(item) for item in applications):
            raise ValueError("request contains an invalid application template id")
        if difficulty not in DIFFICULTIES or resource_class not in RESOURCE_CLASSES:
            raise ValueError("unsupported difficulty or resource class")
        if not 1 <= scale <= 10000 or not 1 <= fault_count <= 64:
            raise ValueError("request scale or fault_count is out of range")
        if fault_count > len(applications):
            raise ValueError("fault_count cannot exceed selected applications")
        if not 2 <= qualification_runs <= 10:
            raise ValueError("qualification_runs must be between 2 and 10")
        if topology_spec:
            candidate = PurePosixPath(topology_spec.replace("\\", "/"))
            if candidate.is_absolute() or ".." in candidate.parts or candidate.suffix != ".json":
                raise ValueError("topology_spec must be a relative JSON path")
        fault_types = tuple(str(item) for item in data.get("fault_types", ()))
        if len(set(fault_types)) != len(fault_types) or any(
            not ID_PATTERN.fullmatch(item) for item in fault_types
        ):
            raise ValueError("fault_types must be unique plugin identities")
        return cls(
            request_id=request_id, objective=objective, topology_id=topology_id,
            applications=applications, seed=seed, difficulty=difficulty,
            scale=scale, fault_count=fault_count, fault_types=fault_types,
            observer_template=str(data.get("observer_template", "network_observer")),
            topology_spec=topology_spec,
            prepare_topology=bool(data.get("prepare_topology", False)),
            execute_lifecycle=bool(data.get("execute_lifecycle", False)),
            qualification_runs=qualification_runs,
            publish=bool(data.get("publish", False)),
            resource_class=resource_class,
        )

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ("applications", "fault_types"):
            value[key] = list(value[key])
        return value

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.to_dict(), sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()


ROLE_OUTPUTS = (
    ("topology_agent", "topology", "topology_ref"),
    ("software_agent", "software", "software"),
    ("service_agent", "services", "service"),
    ("workload_agent", "workloads", "workload"),
    ("fault_agent", "faults", "fault_set"),
    ("test_agent", "tests", "test"),
    ("oracle_agent", "oracle", "oracle"),
    ("scoring_agent", "scoring", "scoring"),
    ("safety_reviewer_agent", "blind_policy", "blind_policy"),
)


def build_agent_tasks(request: BenchmarkRequest) -> Tuple[AgentTask, ...]:
    prefix = request.request_id
    output = {role: f"{prefix}_{suffix}" for role, suffix, _kind in ROLE_OUTPUTS}
    dependencies = {
        "topology_agent": (),
        "software_agent": ("topology_agent",),
        "service_agent": ("topology_agent", "software_agent"),
        "workload_agent": ("topology_agent", "service_agent"),
        "fault_agent": ("topology_agent", "service_agent", "workload_agent"),
        "test_agent": ("topology_agent", "service_agent", "workload_agent", "fault_agent"),
        "oracle_agent": ("test_agent",),
        "scoring_agent": ("test_agent", "oracle_agent"),
        "safety_reviewer_agent": tuple(role for role, _suffix, _kind in ROLE_OUTPUTS[:-1]),
    }
    tasks = []
    for role, _suffix, kind in ROLE_OUTPUTS:
        deps = dependencies[role]
        tasks.append(AgentTask(
            task_id=f"{prefix}_{role}", agent_role=role,
            output_artifact_id=output[role], output_artifact_type=kind,
            dependencies=tuple(f"{prefix}_{item}" for item in deps),
            input_artifacts=tuple(output[item] for item in deps),
            parameters={
                "request_id": request.request_id,
                "request_fingerprint": request.fingerprint,
            },
            max_attempts=3, timeout_seconds=600,
        ))
    return tuple(tasks)


def bundle_spec_for_request(request: BenchmarkRequest) -> BenchmarkBundleSpec:
    artifact_ids = tuple(
        f"{request.request_id}_{suffix}" for _role, suffix, _kind in ROLE_OUTPUTS
    ) + (f"{request.request_id}_lifecycle",)
    return BenchmarkBundleSpec(
        benchmark_id=request.request_id, seed=request.seed,
        artifact_ids=artifact_ids, enabled=False,
    )
