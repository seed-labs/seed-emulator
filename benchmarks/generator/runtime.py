"""Adapter from generated specs to the existing BaseScenario interface."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple, Type

from generator.contracts import inspect_contracts
from generator.models import ScenarioSpec
from generator.storage import validate_manifest_file
from generator.templates import evaluate_verifier, render_scenario


def _class_name(spec: ScenarioSpec) -> str:
    words = [item for item in re.split(r"[^A-Za-z0-9]+", spec.name) if item]
    return "".join(word[:1].upper() + word[1:] for word in words) + "Scenario"


def scenario_class_from_spec(
    spec: ScenarioSpec,
    *,
    suite_id: str = "",
    contract_sha256: str = "",
) -> Type:
    # Import lazily. Importing scenarios.base at module initialization would
    # execute scenarios/__init__.py, which itself imports this loader.
    from scenarios.base import BaseScenario

    def initialize(self):
        BaseScenario.__init__(self)
        self.scenario_seed = self.generated_spec.scenario_seed

    def inject_command(self) -> str:
        return render_scenario(self.generated_spec).inject_command

    def verify_command(self) -> str:
        return render_scenario(self.generated_spec).verify_command

    def fix_command(self) -> str:
        return render_scenario(self.generated_spec).fix_command

    def check_verified(self, output: str) -> bool:
        rendered = render_scenario(self.generated_spec)
        return evaluate_verifier(
            rendered.verifier_kind,
            rendered.verifier_value,
            output,
        )

    expected_roots = (
        {
            "category": spec.fault_type,
            "target_container": list(spec.diagnosis_targets),
            "artifact": spec.diagnosis_artifact,
            "faulty_value": spec.diagnosis_faulty_value,
            "expected_value": spec.diagnosis_expected_value,
        },
    )
    attributes = {
        "__module__": "scenarios.generated",
        "generated_spec": spec,
        "__init__": initialize,
        "get_inject_cmd": inject_command,
        "get_verify_cmd": verify_command,
        "get_fix_cmd": fix_command,
        "check_verified": check_verified,
        "name": spec.name,
        "description": spec.description,
        "topology": spec.topology,
        "fault_type": spec.fault_type,
        "diagnosis_targets": spec.diagnosis_targets,
        "diagnosis_artifact": spec.diagnosis_artifact,
        "diagnosis_faulty_value": spec.diagnosis_faulty_value,
        "diagnosis_expected_value": spec.diagnosis_expected_value,
        "expected_root_causes": expected_roots,
        "benchmark_track": spec.benchmark_track,
        "difficulty": spec.difficulty,
        "main_score_eligible": spec.main_score_eligible,
        "quarantine_reason": spec.quarantine_reason,
        "repair_containers": spec.repair_containers,
        "convergence_timeout": spec.convergence_timeout,
        "fault_settle_seconds": spec.fault_settle_seconds,
        "generated_suite_id": suite_id,
        "generation_fingerprint": spec.fingerprint,
        "generation_contract_sha256": contract_sha256,
    }
    return type(_class_name(spec), (BaseScenario,), attributes)


def load_generated_scenarios(
    benchmarks_dir: Path,
) -> Tuple[Type, ...]:
    """Load enabled suites and fail closed on duplicates or contract drift."""
    root = benchmarks_dir.resolve()
    specs_dir = root / "specs"
    if not specs_dir.is_dir():
        return ()
    snapshot = inspect_contracts(root)
    classes: List[Type] = []
    names = set()
    fingerprints = set()
    for path in sorted(specs_dir.glob("*/manifest.json")):
        manifest = validate_manifest_file(path)
        if not manifest.enabled:
            continue
        if manifest.contract_sha256 != snapshot.sha256:
            raise RuntimeError(
                f"generated suite {manifest.suite_id} targets contract "
                f"{manifest.contract_sha256[:12]}, current is "
                f"{snapshot.sha256[:12]}; regenerate or revalidate it"
            )
        for spec in manifest.scenarios:
            if spec.name in names:
                raise RuntimeError(f"duplicate generated scenario name={spec.name}")
            if spec.fingerprint in fingerprints:
                raise RuntimeError(
                    f"duplicate generated scenario fingerprint={spec.fingerprint}"
                )
            names.add(spec.name)
            fingerprints.add(spec.fingerprint)
            classes.append(
                scenario_class_from_spec(
                    spec,
                    suite_id=manifest.suite_id,
                    contract_sha256=manifest.contract_sha256,
                )
            )
    return tuple(classes)
