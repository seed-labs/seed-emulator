"""The six hand-written top-level models required by the architecture."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Document(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BenchmarkRequest(_Document):
    schema_version: Literal[1] = 1
    topology_source: dict[str, Any]
    objective: str = Field(min_length=1)
    fault: dict[str, Any]
    seed: int = 42


class TopologyFacts(_Document):
    """Pure facts returned by source or runtime topology discovery."""

    schema_version: Literal[1] = 1
    mode: Literal["python_discovered", "runtime_discovered"]
    topology_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    project: str = Field(min_length=1)
    source: dict[str, Any]
    services: list[dict[str, Any]]
    networks: list[dict[str, Any]]
    default_probes: list[dict[str, Any]]
    limits: dict[str, int]
    fingerprint: str = Field(min_length=64, max_length=64)


class FaultCapabilityProposal(_Document):
    """Untrusted LLM proposal; it grants no execution authority."""

    schema_version: Literal[1] = 1
    fault_kind: Literal[
        "container_stopped", "dns_resolver_failure", "firewall_drop", "netem_delay"
    ]
    target_service: str = Field(min_length=1)
    requested_probes: list[
        Literal[
            "container.status",
            "dns.resolver",
            "dns.query",
            "firewall.backend",
            "network.interfaces",
            "network.reachability",
            "netem.qdisc",
        ]
    ] = Field(default_factory=list, max_length=8)
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)
    topology_purpose: str = Field(default="unknown", min_length=1, max_length=500)
    target_role: str = Field(default="unknown", min_length=1, max_length=100)

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "destination", "interface", "delay_ms", "jitter_ms"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError("unknown proposal parameters: " + ", ".join(unknown))
        return value


class FaultCapabilityBinding(_Document):
    """Deterministically verified fault-to-target capability."""

    schema_version: Literal[1] = 1
    binding_id: str = Field(min_length=1)
    fault_kind: str = Field(min_length=1)
    target_service: str = Field(min_length=1)
    driver: str = Field(min_length=1)
    verified: Literal[True] = True
    baseline_probe: dict[str, Any]
    inject_operation: dict[str, Any]
    recovery_operation: dict[str, Any]
    candidate_operations: list[dict[str, Any]]
    evidence_snapshot: dict[str, Any]
    topology_fingerprint: str = Field(min_length=64, max_length=64)
    evidence_fingerprint: str = Field(min_length=64, max_length=64)


class RuntimeContext(_Document):
    schema_version: Literal[1] = 1
    project: str
    target_service: str
    topology: dict[str, Any]
    inventory: dict[str, Any]
    baseline: dict[str, Any]
    capabilities: list[str]


class BenchmarkPlan(_Document):
    schema_version: Literal[1] = 1
    state: Literal["draft", "approved"]
    request: dict[str, Any]
    runtime: dict[str, Any]
    lifecycle: list[dict[str, Any]]
    fingerprint: str


class ExecutionEvent(_Document):
    schema_version: Literal[1] = 1
    sequence: int = Field(ge=0)
    kind: str
    status: Literal["started", "passed", "failed", "rejected"]
    timestamp: str
    data: dict[str, Any]
    fingerprint: str
    ai_invoked: bool = Field(
        default=False,
        description="Whether a lifecycle stage invoked an LLM; deterministic stages must be false",
    )


class RuntimeBenchmarkBundle(_Document):
    schema_version: Literal[1] = 1
    benchmark_id: str
    plan: dict[str, Any]
    agent_view: dict[str, Any]
    capability_grant: dict[str, Any]
    qualification: dict[str, Any]
    evidence_fingerprints: list[str]


class EvaluationRecord(_Document):
    schema_version: Literal[1] = 1
    benchmark_id: str
    provider: dict[str, Any]
    api_trace: list[dict[str, Any]]
    final_probe: dict[str, Any]
    score_report: dict[str, Any]
    cleanup: dict[str, Any]
