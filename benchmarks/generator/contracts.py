"""Read and fingerprint the benchmark interfaces without importing them."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Dict, Tuple


CONTRACT_FILES = (
    "AGENTS.md",
    "docs/NEW_SCENARIO_DEVELOPMENT_GUIDE.md",
    "scenarios/base.py",
    "scenarios/strict_network_software.py",
    "scenarios/__init__.py",
    "benchmark_cli.py",
    "manager.py",
    "agents/ai_agent.py",
    "agents/observations.py",
    "generator/agent.py",
    "generator/contracts.py",
    "generator/models.py",
    "generator/planner.py",
    "generator/templates.py",
    "generator/validator.py",
    "generator/promotion.py",
    "generator/software.py",
    "generator/bundle/__init__.py",
    "generator/bundle/artifacts.py",
    "generator/bundle/models.py",
    "generator/bundle/specs.py",
    "generator/bundle/plugins.py",
    "generator/bundle/security.py",
    "generator/bundle/compiler.py",
    "generator/bundle/coordinator.py",
    "generator/bundle/lifecycle.py",
    "generator/bundle/qualification.py",
    "generator/bundle/pilot.py",
    "generator/bundle/scale.py",
    "generator/bundle/cli.py",
    "generator/bundle/request.py",
    "generator/bundle/templates.py",
    "generator/bundle/workers.py",
    "generator/bundle/quality.py",
    "generator/bundle/publishing.py",
    "generator/bundle/scheduler.py",
    "generator/bundle/pipeline.py",
    "generator/faults/models.py",
    "generator/faults/drivers.py",
    "generator/faults/compiler.py",
    "generator/faults/journal.py",
    "generator/faults/adapters.py",
    "generator/faults/coverage.py",
    "generator/faults/cli.py",
    "generator/faults/scale_validation.py",
    "generator/faults/software.py",
    "generator/topology/bindings.py",
    "generator/topology/compiler.py",
    "generator/topology/models.py",
    "generator/topology/planner.py",
    "generator/topology/registry.py",
)

REQUIRED_BASE_METHODS = {
    "get_inject_cmd",
    "get_verify_cmd",
    "get_fix_cmd",
    "check_verified",
    "run_repair_evaluation",
}

REQUIRED_CLI_OPTIONS = {
    "--agent",
    "--scenario",
    "--all",
    "--topology",
    "--track",
    "--report",
    "--receipt",
    "--repair-eval",
    "--validate-only",
    "--reuse-running",
    "--max-turns",
    "--blind",
    "--no-blind",
}


@dataclass(frozen=True)
class ContractSnapshot:
    benchmarks_dir: Path
    sha256: str
    file_hashes: Dict[str, str]
    base_methods: Tuple[str, ...]
    cli_options: Tuple[str, ...]


def _class_methods(tree: ast.AST, class_name: str) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    raise ValueError(f"required class {class_name} not found")


def inspect_contracts(benchmarks_dir: Path) -> ContractSnapshot:
    """Fail closed when the generator's target interface has drifted."""
    root = benchmarks_dir.resolve()
    digest = hashlib.sha256()
    file_hashes: Dict[str, str] = {}
    contents: Dict[str, bytes] = {}
    for relative in CONTRACT_FILES:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"required benchmark contract is missing: {relative}")
        payload = path.read_bytes()
        contents[relative] = payload
        item_hash = hashlib.sha256(payload).hexdigest()
        file_hashes[relative] = item_hash
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")

    base_tree = ast.parse(
        contents["scenarios/base.py"].decode("utf-8"),
        filename="scenarios/base.py",
    )
    base_methods = _class_methods(base_tree, "BaseScenario")
    missing_methods = REQUIRED_BASE_METHODS - base_methods
    if missing_methods:
        raise ValueError(
            f"BaseScenario contract drift: missing {sorted(missing_methods)}"
        )

    cli_source = contents["benchmark_cli.py"].decode("utf-8")
    missing_options = {
        option for option in REQUIRED_CLI_OPTIONS if option not in cli_source
    }
    if missing_options:
        raise ValueError(
            f"benchmark CLI contract drift: missing {sorted(missing_options)}"
        )

    ai_source = contents["agents/ai_agent.py"].decode("utf-8")
    for field in (
        "repair_commands",
        "target_container",
        "artifact",
        "faulty_value",
        "expected_value",
        "root_causes",
    ):
        if f'"{field}"' not in ai_source:
            raise ValueError(f"AI response contract drift: missing {field}")

    registry_source = contents["scenarios/__init__.py"].decode("utf-8")
    for marker in ("SCENARIO_CATALOG", "SCENARIO_MAP", "get_scenario"):
        if marker not in registry_source:
            raise ValueError(f"scenario registry contract drift: missing {marker}")

    return ContractSnapshot(
        benchmarks_dir=root,
        sha256=digest.hexdigest(),
        file_hashes=file_hashes,
        base_methods=tuple(sorted(base_methods)),
        cli_options=tuple(sorted(REQUIRED_CLI_OPTIONS)),
    )
