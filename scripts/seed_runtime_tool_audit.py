#!/usr/bin/env python3
"""Source-backed audit for the SEED attached-runtime toolchain.

This script answers three concrete questions:
1. What does the low-level harness actually call in `seedemu`?
2. What are SeedOps and SeedAgent actually built on?
3. Where does AI intervene in the attached-runtime path, based on source?
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "mcp-server" / "server.py"
RUNTIME_PATH = REPO_ROOT / "mcp-server" / "runtime.py"
SEEDOPS_PATH = REPO_ROOT / "mcp-server" / "seedops" / "__init__.py"
SEEDOPS_WORKSPACES_PATH = REPO_ROOT / "mcp-server" / "seedops" / "workspaces.py"
SEEDOPS_INVENTORY_PATH = REPO_ROOT / "mcp-server" / "seedops" / "inventory.py"
SEEDOPS_OPS_PATH = REPO_ROOT / "mcp-server" / "seedops" / "ops.py"
SEEDOPS_JOBS_PATH = REPO_ROOT / "mcp-server" / "seedops" / "jobs.py"
SEEDOPS_PLAYBOOKS_PATH = REPO_ROOT / "mcp-server" / "seedops" / "playbooks.py"
SEEDAGENT_SERVER_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "seedagent_mcp" / "server.py"
SEEDAGENT_SERVICE_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "seedagent_mcp" / "service.py"
SEEDAGENT_POLICY_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "seedagent_mcp" / "policy.py"
SEEDAGENT_LLM_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "seedagent_mcp" / "planner_llm.py"
SEEDAGENT_FALLBACK_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "seedagent_mcp" / "planner_fallback.py"
TASK_ENGINE_HITL_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "task_engine" / "hitl.py"
TASK_ENGINE_ORCHESTRATOR_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "task_engine" / "orchestrator.py"
TASK_ENGINE_REGISTRY_PATH = REPO_ROOT / "subrepos" / "seed-agent" / "task_engine" / "registry.py"
TASKS_DIR = REPO_ROOT / "examples" / "agent-missions" / "tasks"


RETURN_TYPE_RULES = {
    "runtime.get_base": "seedemu.layers.Base",
    "runtime.get_emulator": "seedemu.core.Emulator",
    "runtime.find_node_by_name": "seedemu.core.Node",
    "runtime.get_docker_client": "docker.DockerClient",
    "seedemu.layers.Base.getAutonomousSystem": "seedemu.core.AutonomousSystem",
    "seedemu.layers.Base.createAutonomousSystem": "seedemu.core.AutonomousSystem",
    "seedemu.layers.Base.createInternetExchange": "seedemu.core.InternetExchange",
    "seedemu.core.AutonomousSystem.createRouter": "seedemu.core.Node",
    "seedemu.core.AutonomousSystem.createHost": "seedemu.core.Node",
    "seedemu.core.AutonomousSystem.createNetwork": "seedemu.core.Network",
    "seedemu.services.DomainNameService.getZone": "seedemu.services.Zone",
}


SEEDOPS_BACKENDS = {
    "seedops_capabilities": {
        "surface": "capability metadata",
        "backend_flow": [
            "seedops.playbooks.SUPPORTED_ACTIONS",
            "seedops.playbooks.SUPPORTED_PLAYBOOK_VERSION",
        ],
        "design_basis": "Static capability contract for planners and clients; advertises action set and default runtime limits.",
        "source_refs": [
            (SEEDOPS_PLAYBOOKS_PATH, "SUPPORTED_ACTIONS"),
            (SEEDOPS_PLAYBOOKS_PATH, "SUPPORTED_PLAYBOOK_VERSION"),
        ],
    },
    "workspace_create": {
        "surface": "workspace control plane",
        "backend_flow": [
            "SeedOpsStore.create_workspace",
            "SeedOpsStore.insert_event",
        ],
        "design_basis": "Persistent runtime workspace abstraction for attached operations against existing simulations.",
        "source_refs": [
            (SEEDOPS_PATH, "register_tools"),
        ],
    },
    "workspace_list": {
        "surface": "workspace control plane",
        "backend_flow": [
            "WorkspaceManager.list",
        ],
        "design_basis": "Lists persisted attached-runtime workspaces.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.list"),
        ],
    },
    "workspace_get": {
        "surface": "workspace control plane",
        "backend_flow": [
            "WorkspaceManager.get",
        ],
        "design_basis": "Returns attach metadata so clients can reason about current runtime target.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.get"),
        ],
    },
    "workspace_attach_compose": {
        "surface": "runtime attachment",
        "backend_flow": [
            "WorkspaceManager.attach_compose",
            "extract_container_names_from_compose",
            "WorkspaceManager.refresh",
            "InventoryBuilder.build",
            "parse_node_from_labels",
        ],
        "design_basis": "Attaches to a running network by reading compiled docker-compose output and then rebuilding runtime inventory from live containers and SEED labels.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.attach_compose"),
            (SEEDOPS_WORKSPACES_PATH, "extract_container_names_from_compose"),
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.refresh"),
            (SEEDOPS_INVENTORY_PATH, "InventoryBuilder.build"),
            (SEEDOPS_INVENTORY_PATH, "parse_node_from_labels"),
        ],
    },
    "workspace_attach_labels": {
        "surface": "runtime attachment",
        "backend_flow": [
            "WorkspaceManager.attach_labels",
            "WorkspaceManager.refresh",
            "InventoryBuilder.build",
            "parse_node_from_labels",
        ],
        "design_basis": "Attaches to already-running containers by regex + label-prefix scan without needing compose output.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.attach_labels"),
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.refresh"),
            (SEEDOPS_INVENTORY_PATH, "InventoryBuilder.build"),
            (SEEDOPS_INVENTORY_PATH, "parse_node_from_labels"),
        ],
    },
    "workspace_refresh": {
        "surface": "inventory refresh",
        "backend_flow": [
            "WorkspaceManager.refresh",
            "InventoryBuilder.build",
            "parse_node_from_labels",
        ],
        "design_basis": "Rebuilds inventory cache from live Docker state and SEED-emitted labels.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.refresh"),
            (SEEDOPS_INVENTORY_PATH, "InventoryBuilder.build"),
            (SEEDOPS_INVENTORY_PATH, "parse_node_from_labels"),
        ],
    },
    "events_list": {
        "surface": "audit trail",
        "backend_flow": [
            "WorkspaceManager.list_events",
        ],
        "design_basis": "Exposes the persistent audit/event log for attached-runtime actions.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.list_events"),
        ],
    },
    "inventory_list_nodes": {
        "surface": "inventory query",
        "backend_flow": [
            "WorkspaceManager.list_nodes",
            "filter_nodes",
        ],
        "design_basis": "Selector-based inventory query over cached node refs extracted from SEED labels.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.list_nodes"),
            (REPO_ROOT / "mcp-server" / "seedops" / "selectors.py", "filter_nodes"),
        ],
    },
    "inventory_get_node": {
        "surface": "inventory query",
        "backend_flow": [
            "WorkspaceManager.get_node",
        ],
        "design_basis": "Returns one attached node reference for targeted diagnostics.",
        "source_refs": [
            (SEEDOPS_WORKSPACES_PATH, "WorkspaceManager.get_node"),
        ],
    },
    "ops_exec": {
        "surface": "batch runtime operation",
        "backend_flow": [
            "OpsService.exec",
            "OpsService._pick_exec_backend",
            "OpsService._run_shell",
            "docker exec / Docker SDK exec_run",
        ],
        "design_basis": "Runs bounded shell commands across selected containers with timeout, truncation, and per-node results.",
        "source_refs": [
            (SEEDOPS_OPS_PATH, "OpsService.exec"),
            (SEEDOPS_OPS_PATH, "OpsService._pick_exec_backend"),
            (SEEDOPS_OPS_PATH, "OpsService._run_shell"),
        ],
    },
    "ops_logs": {
        "surface": "batch observation",
        "backend_flow": [
            "OpsService.logs",
            "docker SDK container.logs",
        ],
        "design_basis": "Parallel log collection on selected containers with truncation and failure summaries.",
        "source_refs": [
            (SEEDOPS_OPS_PATH, "OpsService.logs"),
        ],
    },
    "routing_bgp_summary": {
        "surface": "routing observation",
        "backend_flow": [
            "OpsService.bgp_summary",
            "OpsService._run_shell",
            "birdc show protocols",
        ],
        "design_basis": "Runs BIRD inspection across selected routers and summarizes up/down BGP sessions.",
        "source_refs": [
            (SEEDOPS_OPS_PATH, "OpsService.bgp_summary"),
            (SEEDOPS_OPS_PATH, "OpsService._run_shell"),
        ],
    },
    "playbook_validate": {
        "surface": "job planning contract",
        "backend_flow": [
            "parse_playbook_yaml",
        ],
        "design_basis": "Validates the attached-runtime playbook DSL before execution.",
        "source_refs": [
            (SEEDOPS_PLAYBOOKS_PATH, "parse_playbook_yaml"),
        ],
    },
    "playbook_run": {
        "surface": "job orchestration",
        "backend_flow": [
            "JobManager.start_playbook",
            "JobManager._run_playbook_job",
            "JobManager._execute_step",
        ],
        "design_basis": "Launches a background playbook job and records step-level artifacts, status, and rollback evidence.",
        "source_refs": [
            (SEEDOPS_JOBS_PATH, "JobManager.start_playbook"),
            (SEEDOPS_JOBS_PATH, "JobManager._run_playbook_job"),
            (SEEDOPS_JOBS_PATH, "JobManager._execute_step"),
        ],
    },
    "jobs_list": {
        "surface": "job tracking",
        "backend_flow": [
            "SeedOpsStore.list_jobs",
        ],
        "design_basis": "Lists background playbook and collector jobs.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "store.py", "SeedOpsStore.list_jobs"),
        ],
    },
    "job_get": {
        "surface": "job tracking",
        "backend_flow": [
            "SeedOpsStore.get_job",
        ],
        "design_basis": "Fetches current job status, message, and summary data.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "store.py", "SeedOpsStore.get_job"),
        ],
    },
    "job_steps_list": {
        "surface": "job tracking",
        "backend_flow": [
            "SeedOpsStore.list_job_steps",
        ],
        "design_basis": "Returns step timeline for execution evidence and troubleshooting.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "store.py", "SeedOpsStore.list_job_steps"),
        ],
    },
    "job_cancel": {
        "surface": "job tracking",
        "backend_flow": [
            "JobManager.cancel_job",
        ],
        "design_basis": "Signals an in-flight playbook or collector to stop safely.",
        "source_refs": [
            (SEEDOPS_JOBS_PATH, "JobManager.cancel_job"),
        ],
    },
    "collector_start": {
        "surface": "periodic observation",
        "backend_flow": [
            "JobManager.start_collector",
            "JobManager._run_collector_job",
        ],
        "design_basis": "Starts a background sampler that periodically snapshots inventory and optional BGP summary.",
        "source_refs": [
            (SEEDOPS_JOBS_PATH, "JobManager.start_collector"),
            (SEEDOPS_JOBS_PATH, "JobManager._run_collector_job"),
        ],
    },
    "snapshots_list": {
        "surface": "periodic observation",
        "backend_flow": [
            "SeedOpsStore.list_snapshots",
        ],
        "design_basis": "Lists lightweight collector snapshots recorded by workspace and type.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "store.py", "SeedOpsStore.list_snapshots"),
        ],
    },
    "artifacts_list": {
        "surface": "artifact retrieval",
        "backend_flow": [
            "SeedOpsStore.list_artifacts",
        ],
        "design_basis": "Lists evidence artifacts emitted by jobs, including PCAP and logs.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "store.py", "SeedOpsStore.list_artifacts"),
        ],
    },
    "artifact_read": {
        "surface": "artifact retrieval",
        "backend_flow": [
            "ArtifactManager.read_text",
        ],
        "design_basis": "Reads text artifacts directly for concise evidence review.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "artifacts.py", "ArtifactManager.read_text"),
        ],
    },
    "artifact_read_chunk": {
        "surface": "artifact retrieval",
        "backend_flow": [
            "ArtifactManager.read_chunk",
        ],
        "design_basis": "Streams binary or large artifacts in chunks for client-side download.",
        "source_refs": [
            (REPO_ROOT / "mcp-server" / "seedops" / "artifacts.py", "ArtifactManager.read_chunk"),
        ],
    },
    "maintenance_prune_workspace": {
        "surface": "maintenance",
        "backend_flow": [
            "SeedOpsStore.delete_workspace",
            "ArtifactManager.prune_workspace",
        ],
        "design_basis": "Prunes workspace metadata and stored artifacts to control cost and drift.",
        "source_refs": [
            (SEEDOPS_PATH, "register_tools"),
            (REPO_ROOT / "mcp-server" / "seedops" / "artifacts.py", "ArtifactManager.prune_workspace"),
        ],
    },
}


SEEDAGENT_BACKENDS = {
    "seed_agent_policy_check": {
        "surface": "policy gate",
        "backend_flow": [
            "SeedAgentService.policy_check",
            "evaluate_command_policy",
            "resolve_policy_profile",
        ],
        "design_basis": "Bounded command-policy check before runtime mutation or risky shell execution.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.policy_check"),
            (SEEDAGENT_POLICY_PATH, "evaluate_command_policy"),
            (SEEDAGENT_POLICY_PATH, "resolve_policy_profile"),
        ],
    },
    "seed_agent_plan": {
        "surface": "high-level planning",
        "backend_flow": [
            "SeedAgentService.compile_playbook",
            "SeedOpsAPI.seedops_capabilities",
            "SeedAgentService._ensure_workspace_context",
            "compile_llm_plan",
            "compile_fallback_plan",
            "check_playbook_policy",
        ],
        "design_basis": "Builds a SeedOps playbook from request + runtime context, with LLM-primary and template fallback paths.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.compile_playbook"),
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService._ensure_workspace_context"),
            (SEEDAGENT_LLM_PATH, "compile_llm_plan"),
            (SEEDAGENT_FALLBACK_PATH, "compile_fallback_plan"),
            (SEEDAGENT_POLICY_PATH, "check_playbook_policy"),
        ],
    },
    "seed_agent_run": {
        "surface": "high-level execution",
        "backend_flow": [
            "SeedAgentService.run_ops",
            "SeedAgentService.compile_playbook",
            "SeedAgentService._run_compiled_playbook",
            "SeedOpsAPI.playbook_run",
            "SeedOpsAPI.artifacts_list",
        ],
        "design_basis": "Runs the full plan/execute/follow/download loop and returns environment snapshot plus verification summary.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.run_ops"),
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService._run_compiled_playbook"),
        ],
    },
    "seed_agent_artifacts_download": {
        "surface": "artifact retrieval",
        "backend_flow": [
            "SeedAgentService.download_artifacts",
            "SeedOpsAPI.download_artifact",
            "SeedOpsAPI.artifact_read_chunk",
        ],
        "design_basis": "Client-side artifact download loop for post-run evidence collection.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.download_artifacts"),
            (REPO_ROOT / "subrepos" / "seed-agent" / "mcp_client" / "seedops_api.py", "SeedOpsAPI.download_artifact"),
            (REPO_ROOT / "subrepos" / "seed-agent" / "mcp_client" / "seedops_api.py", "SeedOpsAPI.artifact_read_chunk"),
        ],
    },
    "seed_agent_task_catalog": {
        "surface": "mission/task control",
        "backend_flow": [
            "SeedAgentService.task_catalog",
            "TaskOrchestrator.task_catalog",
            "TaskRegistry.list_summary",
        ],
        "design_basis": "Exposes the mission/task catalog with contract fields already normalized for clients.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.task_catalog"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_catalog"),
            (TASK_ENGINE_REGISTRY_PATH, "TaskRegistry.list_summary"),
        ],
    },
    "seed_agent_task_begin": {
        "surface": "mission/task control",
        "backend_flow": [
            "SeedAgentService.task_begin",
            "TaskOrchestrator.task_begin",
            "evaluate_hitl",
        ],
        "design_basis": "Starts a task session, asks only missing inputs, and triggers confirmation when policy requires it.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.task_begin"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_begin"),
            (TASK_ENGINE_HITL_PATH, "evaluate_hitl"),
        ],
    },
    "seed_agent_task_reply": {
        "surface": "mission/task control",
        "backend_flow": [
            "SeedAgentService.task_reply",
            "TaskOrchestrator.task_reply",
            "evaluate_hitl",
        ],
        "design_basis": "Accumulates user answers and recomputes missing input / confirmation state.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.task_reply"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_reply"),
            (TASK_ENGINE_HITL_PATH, "evaluate_hitl"),
        ],
    },
    "seed_agent_task_execute": {
        "surface": "mission/task control",
        "backend_flow": [
            "SeedAgentService.task_execute",
            "TaskOrchestrator.task_execute",
            "evaluate_hitl",
            "SeedAgentService.run_ops",
        ],
        "design_basis": "Executes a prepared task session only after required inputs and approval token are satisfied.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.task_execute"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_execute"),
            (TASK_ENGINE_HITL_PATH, "evaluate_hitl"),
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.run_ops"),
        ],
    },
    "seed_agent_task_status": {
        "surface": "mission/task control",
        "backend_flow": [
            "SeedAgentService.task_status",
            "TaskOrchestrator.task_status",
        ],
        "design_basis": "Returns the last execution refs and decision log for a task session.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.task_status"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_status"),
        ],
    },
}


AI_INTERVENTION_POINTS = [
    {
        "name": "runtime context grounding",
        "what_ai_uses": "workspace attachment summary, refreshed inventory, and scale hints",
        "why_it_matters": "The planner sees the running network shape before choosing selectors or step granularity.",
        "source_refs": [
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService._ensure_workspace_context"),
            (SEEDAGENT_LLM_PATH, "compile_llm_plan"),
        ],
    },
    {
        "name": "scope and selector choice",
        "what_ai_uses": "runtime_context.inventory_summary plus selector normalization",
        "why_it_matters": "The system steers the model toward bounded selectors instead of fleet-wide shelling.",
        "source_refs": [
            (SEEDAGENT_LLM_PATH, "compile_llm_plan"),
            (SEEDAGENT_SERVICE_PATH, "_promote_selector_fields"),
        ],
    },
    {
        "name": "policy gating and downgrade",
        "what_ai_uses": "policy profiles read_only/net_ops/danger and playbook validation results",
        "why_it_matters": "Risky plans are blocked or downgraded to deterministic fallback when they violate policy.",
        "source_refs": [
            (SEEDAGENT_POLICY_PATH, "check_playbook_policy"),
            (SEEDAGENT_POLICY_PATH, "evaluate_command_policy"),
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.compile_playbook"),
        ],
    },
    {
        "name": "llm-primary with template fallback",
        "what_ai_uses": "LLM output only when schema-valid and policy-valid; otherwise fallback templates",
        "why_it_matters": "The LLM is not the only execution path, which keeps runtime control usable when model output is weak.",
        "source_refs": [
            (SEEDAGENT_LLM_PATH, "compile_llm_plan"),
            (SEEDAGENT_FALLBACK_PATH, "compile_fallback_plan"),
            (SEEDAGENT_SERVICE_PATH, "SeedAgentService.compile_playbook"),
        ],
    },
    {
        "name": "task-session HITL",
        "what_ai_uses": "task contract fields, missing-input checks, policy-by-stage, approval token",
        "why_it_matters": "Live drills and elevated actions do not execute from an underspecified chat turn.",
        "source_refs": [
            (TASK_ENGINE_HITL_PATH, "evaluate_hitl"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_begin"),
            (TASK_ENGINE_ORCHESTRATOR_PATH, "TaskOrchestrator.task_execute"),
        ],
    },
]


@dataclass
class ToolInfo:
    name: str
    lineno: int
    path: Path
    call_targets: list[str]


def git_branch(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def source_ref(path: Path, lineno: int | None = None) -> str:
    rel = path.relative_to(REPO_ROOT)
    if lineno:
        return f"{rel}:{lineno}"
    return str(rel)


def read_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def collect_imports(tree: ast.AST) -> dict[str, str]:
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                if node.module == "runtime" and alias.name == "runtime":
                    imports[local] = "runtime"
                    continue
                imports[local] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                imports[local] = alias.name
    return imports


def call_name(expr: ast.AST, var_types: dict[str, str], imports: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Name):
        return var_types.get(expr.id) or imports.get(expr.id) or expr.id
    if isinstance(expr, ast.Attribute):
        base = call_name(expr.value, var_types, imports)
        if not base:
            return expr.attr
        return f"{base}.{expr.attr}"
    if isinstance(expr, ast.Call):
        return call_name(expr.func, var_types, imports)
    return None


def infer_return_type(node: ast.AST, var_types: dict[str, str], imports: dict[str, str]) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    callee = normalize_call(call_name(node.func, var_types, imports) or "")
    if not callee:
        return None
    if callee in RETURN_TYPE_RULES:
        return RETURN_TYPE_RULES[callee]
    if callee.startswith("seedemu."):
        last = callee.rsplit(".", 1)[-1]
        if last and last[:1].isupper():
            return callee
    return None


def normalize_call(name: str) -> str:
    out = name or ""
    out = out.replace("runtime.runtime.", "runtime.")
    out = out.replace("runtime.runtime", "runtime")
    return out


class CallCollector(ast.NodeVisitor):
    def __init__(self, imports: dict[str, str]):
        self.imports = imports
        self.var_types: dict[str, str] = {}
        self.calls: list[str] = []

    def visit_Assign(self, node: ast.Assign) -> Any:
        self.visit(node.value)
        inferred = infer_return_type(node.value, self.var_types, self.imports)
        if inferred:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.var_types[target.id] = inferred

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if node.value is not None:
            self.visit(node.value)
            inferred = infer_return_type(node.value, self.var_types, self.imports)
            if inferred and isinstance(node.target, ast.Name):
                self.var_types[node.target.id] = inferred

    def visit_With(self, node: ast.With) -> Any:
        for item in node.items:
            self.visit(item.context_expr)
            inferred = infer_return_type(item.context_expr, self.var_types, self.imports)
            if inferred and isinstance(item.optional_vars, ast.Name):
                self.var_types[item.optional_vars.id] = inferred
        for stmt in node.body:
            self.visit(stmt)

    def visit_Call(self, node: ast.Call) -> Any:
        callee = normalize_call(call_name(node.func, self.var_types, self.imports) or "")
        if callee:
            self.calls.append(callee)
        for child in ast.iter_child_nodes(node):
            self.visit(child)


def is_tool_decorator(decorator: ast.AST, owner: str) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == owner
        and decorator.func.attr == "tool"
    )


def extract_tool_functions(path: Path, *, owner: str, parent_func: str | None = None) -> list[ToolInfo]:
    tree = read_module(path)
    imports = collect_imports(tree)
    nodes: list[ast.FunctionDef] = []

    if parent_func is None:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                nodes.append(node)
    else:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == parent_func:
                for inner in node.body:
                    if isinstance(inner, ast.FunctionDef):
                        nodes.append(inner)
                break

    tools: list[ToolInfo] = []
    for node in nodes:
        if not any(is_tool_decorator(deco, owner) for deco in node.decorator_list):
            continue
        collector = CallCollector(imports)
        for stmt in node.body:
            collector.visit(stmt)
        seen: set[str] = set()
        ordered_calls: list[str] = []
        for current in collector.calls:
            if current not in seen:
                seen.add(current)
                ordered_calls.append(current)
        tools.append(
            ToolInfo(
                name=node.name,
                lineno=node.lineno,
                path=path,
                call_targets=ordered_calls,
            )
        )
    return tools


def find_symbol_lineno(path: Path, qualname: str) -> int | None:
    parts = [part for part in qualname.split(".") if part]
    if not parts:
        return None
    tree = read_module(path)

    def _walk(nodes: list[ast.stmt], remaining: list[str]) -> int | None:
        if not remaining:
            return None
        current = remaining[0]
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == current:
                if len(remaining) == 1:
                    return node.lineno
                if isinstance(node, ast.ClassDef):
                    return _walk(node.body, remaining[1:])
                return _walk(node.body, remaining[1:])
        return None

    return _walk(list(tree.body), parts)


def extract_seedemu_usage(paths: list[Path]) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        tree = read_module(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("seedemu."):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    grouped[node.module].add(alias.name)
    return {module: sorted(values) for module, values in sorted(grouped.items())}


def summarize_server_tool(tool: ToolInfo) -> dict[str, Any]:
    seedemu_calls = [call for call in tool.call_targets if call.startswith("seedemu.")]
    runtime_calls = [call for call in tool.call_targets if call.startswith("runtime.")]
    return {
        "name": tool.name,
        "source": source_ref(tool.path, tool.lineno),
        "seedemu_calls": seedemu_calls,
        "runtime_calls": runtime_calls,
        "all_calls": tool.call_targets,
    }


def summarize_wrapper_tool(tool: ToolInfo, backend_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    backend = backend_map.get(tool.name, {})
    refs = []
    for ref_path, symbol in backend.get("source_refs", []):
        refs.append(source_ref(ref_path, find_symbol_lineno(ref_path, symbol)))
    return {
        "name": tool.name,
        "source": source_ref(tool.path, tool.lineno),
        "wrapper_calls": tool.call_targets,
        "surface": backend.get("surface", "unclassified"),
        "design_basis": backend.get("design_basis", ""),
        "backend_flow": backend.get("backend_flow", []),
        "backend_refs": refs,
    }


def supported_actions() -> list[str]:
    tree = read_module(SEEDOPS_PLAYBOOKS_PATH)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SUPPORTED_ACTIONS":
                value = ast.literal_eval(node.value)
                if isinstance(value, (set, list, tuple)):
                    return sorted(str(action) for action in value)
    return []


def load_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(TASKS_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        tasks.append(
            {
                "task_id": raw.get("task_id"),
                "title": raw.get("title"),
                "track": raw.get("track"),
                "baseline": raw.get("baseline"),
                "scenario_class": raw.get("scenario_class"),
                "policy_by_stage": raw.get("policy_by_stage") or {},
                "rollback_required": bool(raw.get("rollback_required")),
                "evidence_requirements": raw.get("evidence_requirements") or [],
                "acceptance_checks": raw.get("acceptance_checks") or [],
                "source": source_ref(path),
            }
        )
    return tasks


def build_ai_intervention_points() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in AI_INTERVENTION_POINTS:
        refs = []
        for ref_path, symbol in item["source_refs"]:
            refs.append(source_ref(ref_path, find_symbol_lineno(ref_path, symbol)))
        rows.append(
            {
                "name": item["name"],
                "what_ai_uses": item["what_ai_uses"],
                "why_it_matters": item["why_it_matters"],
                "source_refs": refs,
            }
        )
    return rows


def build_audit() -> dict[str, Any]:
    server_tools = extract_tool_functions(SERVER_PATH, owner="mcp")
    seedops_tools = extract_tool_functions(SEEDOPS_PATH, owner="mcp", parent_func="register_tools")
    seedagent_tools = extract_tool_functions(SEEDAGENT_SERVER_PATH, owner="app", parent_func="register_tools")
    tasks = load_tasks()

    canonical_seedagent = [tool for tool in seedagent_tools if tool.name.startswith("seed_agent_")]
    alias_seedagent = [tool for tool in seedagent_tools if not tool.name.startswith("seed_agent_")]

    return {
        "audit_date": "2026-04-02",
        "repo": {
            "root": str(REPO_ROOT),
            "root_branch": git_branch(REPO_ROOT),
            "seed_agent_branch": git_branch(REPO_ROOT / "subrepos" / "seed-agent"),
        },
        "counts": {
            "mcp_server_tools": len(server_tools),
            "seedops_tools": len(seedops_tools),
            "seedagent_canonical_tools": len(canonical_seedagent),
            "seedagent_alias_tools": len(alias_seedagent),
            "seedops_playbook_actions": len(supported_actions()),
            "task_count": len(tasks),
        },
        "key_findings": [
            "Attached runtime is built on compiled compose output plus SEED docker labels, not on reconstructing topology from scratch.",
            "Low-level mcp-server tools directly use seedemu modeling APIs; SeedOps mostly operates on Docker/container inventory and playbook orchestration; SeedAgent adds planning, policy, HITL, and task-state control.",
            "AI intervention happens after runtime grounding and before execution: selector choice, policy-constrained planning, fallback, and task-stage confirmation.",
        ],
        "seedemu_public_entrypoints_used": extract_seedemu_usage([SERVER_PATH, RUNTIME_PATH]),
        "runtime_kernel": {
            "source": source_ref(RUNTIME_PATH),
            "notes": [
                "EmulatorRuntime owns Emulator + Base singletons and lifecycle state.",
                "The attached-runtime path reuses this object graph for build-time APIs but SeedOps runtime control is separate and inventory-driven.",
            ],
            "refs": [
                source_ref(RUNTIME_PATH, find_symbol_lineno(RUNTIME_PATH, "EmulatorRuntime.reset")),
                source_ref(RUNTIME_PATH, find_symbol_lineno(RUNTIME_PATH, "EmulatorRuntime.lifecycle_contract")),
                source_ref(RUNTIME_PATH, find_symbol_lineno(RUNTIME_PATH, "EmulatorRuntime.find_node_by_name")),
            ],
        },
        "mcp_server": {
            "tool_count": len(server_tools),
            "tools": [summarize_server_tool(tool) for tool in server_tools],
        },
        "seedops": {
            "tool_count": len(seedops_tools),
            "supported_actions": supported_actions(),
            "attached_runtime_basis": {
                "compose_source": source_ref(SEEDOPS_WORKSPACES_PATH, find_symbol_lineno(SEEDOPS_WORKSPACES_PATH, "extract_container_names_from_compose")),
                "label_inventory": source_ref(SEEDOPS_INVENTORY_PATH, find_symbol_lineno(SEEDOPS_INVENTORY_PATH, "parse_node_from_labels")),
                "inventory_builder": source_ref(SEEDOPS_INVENTORY_PATH, find_symbol_lineno(SEEDOPS_INVENTORY_PATH, "InventoryBuilder.build")),
                "summary": "SeedOps attaches to existing runtime through docker-compose container_name and the SEED label namespace org.seedsecuritylabs.seedemu.meta.*.",
            },
            "tools": [summarize_wrapper_tool(tool, SEEDOPS_BACKENDS) for tool in seedops_tools],
        },
        "seedagent": {
            "canonical_tool_count": len(canonical_seedagent),
            "alias_tool_count": len(alias_seedagent),
            "canonical_tools": [summarize_wrapper_tool(tool, SEEDAGENT_BACKENDS) for tool in canonical_seedagent],
            "alias_tools": [summarize_wrapper_tool(tool, SEEDAGENT_BACKENDS) for tool in alias_seedagent],
            "ai_intervention_points": build_ai_intervention_points(),
            "task_contract": {
                "required_fields": [
                    "task_id",
                    "title",
                    "scenario_class",
                    "policy_by_stage",
                    "rollback_required",
                    "evidence_requirements",
                    "acceptance_checks",
                ],
                "approval_token": "YES_RUN_DYNAMIC_FAULTS",
                "tasks": tasks,
            },
        },
    }


def render_markdown(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# SEED Attached-Runtime Source Audit")
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Date: {data['audit_date']}")
    lines.append(f"- Root branch: `{data['repo']['root_branch']}`")
    lines.append(f"- Seed-Agent branch: `{data['repo']['seed_agent_branch']}`")
    lines.append(
        "- Counts: "
        f"mcp-server={data['counts']['mcp_server_tools']}, "
        f"seedops={data['counts']['seedops_tools']}, "
        f"seedagent canonical={data['counts']['seedagent_canonical_tools']}, "
        f"aliases={data['counts']['seedagent_alias_tools']}, "
        f"playbook actions={data['counts']['seedops_playbook_actions']}, "
        f"tasks={data['counts']['task_count']}"
    )
    lines.append("")
    lines.append("## Hard Findings")
    for item in data["key_findings"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## seedemu APIs Used By Harness")
    for module, symbols in data["seedemu_public_entrypoints_used"].items():
        lines.append(f"- `{module}`: {', '.join(symbols)}")
    lines.append("")
    lines.append("## Runtime Kernel")
    for note in data["runtime_kernel"]["notes"]:
        lines.append(f"- {note}")
    for ref in data["runtime_kernel"]["refs"]:
        lines.append(f"- Ref: `{ref}`")
    lines.append("")
    lines.append("## mcp-server Tool Surface")
    for tool in data["mcp_server"]["tools"]:
        seedemu_calls = ", ".join(tool["seedemu_calls"][:6]) or "none"
        runtime_calls = ", ".join(tool["runtime_calls"][:4]) or "none"
        lines.append(
            f"- `{tool['name']}` at `{tool['source']}` "
            f"seedemu=[{seedemu_calls}] runtime=[{runtime_calls}]"
        )
    lines.append("")
    lines.append("## SeedOps Attached-Runtime Basis")
    basis = data["seedops"]["attached_runtime_basis"]
    lines.append(f"- {basis['summary']}")
    lines.append(f"- Compose attach ref: `{basis['compose_source']}`")
    lines.append(f"- Label inventory ref: `{basis['label_inventory']}`")
    lines.append(f"- Inventory builder ref: `{basis['inventory_builder']}`")
    lines.append("")
    lines.append("### SeedOps Tools")
    for tool in data["seedops"]["tools"]:
        flow = " -> ".join(tool["backend_flow"])
        refs = ", ".join(tool["backend_refs"])
        lines.append(f"- `{tool['name']}` at `{tool['source']}`")
        lines.append(f"  surface={tool['surface']}; flow={flow}")
        lines.append(f"  refs={refs}")
    lines.append("")
    lines.append("## SeedAgent High-Level Control")
    lines.append("### Canonical Tools")
    for tool in data["seedagent"]["canonical_tools"]:
        flow = " -> ".join(tool["backend_flow"])
        refs = ", ".join(tool["backend_refs"])
        lines.append(f"- `{tool['name']}` at `{tool['source']}`")
        lines.append(f"  surface={tool['surface']}; flow={flow}")
        lines.append(f"  refs={refs}")
    lines.append("")
    lines.append("### Compatibility Aliases")
    for tool in data["seedagent"]["alias_tools"]:
        flow = " -> ".join(tool["backend_flow"])
        refs = ", ".join(tool["backend_refs"])
        lines.append(f"- `{tool['name']}` at `{tool['source']}`")
        lines.append(f"  surface={tool['surface']}; flow={flow}")
        lines.append(f"  refs={refs}")
    lines.append("")
    lines.append("## AI Intervention Points")
    for item in data["seedagent"]["ai_intervention_points"]:
        refs = ", ".join(item["source_refs"])
        lines.append(f"- `{item['name']}`: {item['what_ai_uses']}")
        lines.append(f"  why={item['why_it_matters']}")
        lines.append(f"  refs={refs}")
    lines.append("")
    lines.append("## Mission Task Contract")
    lines.append(
        "- Required public fields: "
        + ", ".join(data["seedagent"]["task_contract"]["required_fields"])
    )
    lines.append(f"- Approval token: `{data['seedagent']['task_contract']['approval_token']}`")
    for task in data["seedagent"]["task_contract"]["tasks"]:
        lines.append(
            f"- `{task['task_id']}` ({task['track']}/{task['baseline']}) "
            f"scenario={task['scenario_class']} rollback={task['rollback_required']} source=`{task['source']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit SEED attached-runtime tool/API design from source")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--out", default="", help="Optional output file")
    args = parser.parse_args()

    data = build_audit()
    text = json.dumps(data, indent=2, ensure_ascii=False) if args.format == "json" else render_markdown(data)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
