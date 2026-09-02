"""Scenario loading and validation: every run is driven by a scenario file.

A scenario file carries every run-specific value that used to be hardcoded:
topology source, fault parameters, the action contract (names, tool mappings,
redaction fields, per-action arguments), prompts, scoring weights, and naming.
Workflow code only executes what the scenario declares.
"""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TopologySpec(BaseModel):
    """Topology provenance: Python discovery artifact or running Compose project."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["python_discovered", "runtime_discovered"]
    script_path: str | None = None
    descriptor_fingerprint: str | None = None
    artifact_id: str | None = None
    compose_path: str | None = None
    project: str | None = None
    interpretation: dict[str, Any] = Field(default_factory=dict)


class FaultSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    target_service: str
    probe_tool: str
    inject_tool: str
    recover_tool: str
    probe_arguments: dict[str, Any] = Field(default_factory=dict)
    inject_arguments: dict[str, Any] = Field(default_factory=dict)
    healthy_field: str = "healthy"
    baseline_value: bool = True
    fault_value: bool = False


class GrantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_calls: int = Field(ge=1)
    ttl_seconds: int = Field(ge=1)
    tools: list[str]


class ActionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str | None = None
    terminal: bool = False
    description: str
    fields: list[str] = Field(default_factory=list)
    arguments: dict[str, Any] = Field(default_factory=dict)


class PromptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_system: str
    inspect_system: str
    agent_view_objective: str


class ScoringSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_success: int = 60
    authorization: int = 20
    efficiency: int = 20
    base_turns: int = 3
    penalty_per_turn: int = 5


class NamingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_prefix: str
    project_alias: str
    inspect_task_name: str
    sample_id: str


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    id: str
    topology: TopologySpec
    capability_binding: dict[str, Any] | None = None
    project: str
    fault: FaultSpec
    seed: int
    grant: GrantSpec
    capabilities: list[str]
    actions: dict[str, ActionSpec]
    prompts: PromptSpec
    scoring: ScoringSpec
    naming: NamingSpec

    @field_validator("actions")
    @classmethod
    def _validate_actions(cls, actions: dict[str, ActionSpec]) -> dict[str, ActionSpec]:
        if not actions:
            raise ValueError("actions must not be empty")
        terminal = [name for name, spec in actions.items() if spec.terminal]
        if terminal != ["finish"]:
            raise ValueError("finish must be the only terminal action")
        for name, spec in actions.items():
            if name == "finish":
                if spec.tool is not None:
                    raise ValueError("finish must not declare a tool mapping")
            elif spec.tool is None:
                raise ValueError(f"action {name!r} requires a tool mapping")
        return actions

    @model_validator(mode="after")
    def _validate_capabilities(self) -> "Scenario":
        expected = sorted(
            name for name, spec in self.actions.items() if not spec.terminal
        )
        if sorted(self.capabilities) != expected:
            raise ValueError("capabilities must list exactly the non-terminal actions")
        action_tools = sorted(
            spec.tool for spec in self.actions.values() if spec.tool is not None
        )
        if sorted(self.grant.tools) != action_tools:
            raise ValueError(
                "grant tools must match exactly the non-terminal action tools"
            )
        candidate_tools = {
            spec.tool for spec in self.actions.values() if spec.tool is not None
        }

        def _is_generic(tool: str | None) -> bool:
            return bool(tool and tool.startswith("operation."))

        # Generic operation tools may appear on both sides with different
        # pinned arguments (e.g. DNS set_nameserver inject vs. repair), so the
        # separation is enforced at operation identity granularity for them.
        inject_identity = (
            self.fault.inject_tool,
            json.dumps(self.fault.inject_arguments or {}, sort_keys=True),
        )
        candidate_identities = {
            (spec.tool, json.dumps(spec.arguments or {}, sort_keys=True))
            for spec in self.actions.values()
            if spec.tool is not None
        }
        if inject_identity in candidate_identities:
            raise ValueError(
                "fault injection operation must never be candidate-grantable "
                "(same tool and arguments)"
            )
        # Legacy benchmark.* inject/recover tools carry defaulted destructive
        # arguments and must never enter a candidate grant, whatever the args.
        for author_tool in (self.fault.inject_tool, self.fault.recover_tool):
            if author_tool and not _is_generic(author_tool) and author_tool in candidate_tools:
                raise ValueError(
                    "legacy fault mutation tools must never be candidate-grantable"
                )
        return self

    @model_validator(mode="after")
    def _validate_topology_binding(self) -> "Scenario":
        if self.topology.mode == "python_discovered":
            if not all(
                (
                    self.topology.script_path,
                    self.topology.descriptor_fingerprint,
                    self.topology.artifact_id,
                    self.topology.compose_path,
                )
            ):
                raise ValueError(
                    "python_discovered topology requires script, descriptor, artifact, and Compose"
                )
            if not self.topology.project or self.topology.project != self.project:
                raise ValueError(
                    "python_discovered topology project must match the scenario project"
                )
        else:
            if (
                self.topology.script_path
                or self.topology.artifact_id
                or self.topology.compose_path
            ):
                raise ValueError(
                    "runtime_discovered topology must not declare Python artifacts"
                )
            if not self.topology.project:
                raise ValueError("runtime_discovered topology requires a project")
            if self.topology.project != self.project:
                raise ValueError(
                    "runtime_discovered topology project must match the scenario project"
                )
        return self

    @model_validator(mode="after")
    def _validate_capability_binding(self) -> "Scenario":
        binding = self.capability_binding
        if binding is None:
            raise ValueError("capability_binding is required; legacy Tool Service fault lifecycles are unsupported")
        if binding.get("fault_kind") != self.fault.kind:
            raise ValueError("capability binding fault must match the scenario fault")
        if binding.get("target_service") != self.fault.target_service:
            raise ValueError("capability binding target must match the scenario target")
        if (
            binding.get("topology_fingerprint") != self.topology.descriptor_fingerprint
            and self.topology.mode == "python_discovered"
        ):
            raise ValueError("capability binding topology fingerprint drifted")
        return self

    @property
    def allowed_actions(self) -> list[str]:
        """Every declared action, in declaration order (finish included)."""

        return list(self.actions)

    @property
    def finish_action(self) -> str:
        """Name of the terminal completion action."""

        return next(name for name, spec in self.actions.items() if spec.terminal)


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate one explicit scenario file."""

    scenario_path = Path(path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"scenario not found: {scenario_path}")
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    return Scenario.model_validate(raw)
