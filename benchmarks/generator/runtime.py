"""Adapter from generated specs to the existing BaseScenario interface."""

from __future__ import annotations

from pathlib import Path
import re
import time
from typing import List, Tuple, Type

from generator.contracts import inspect_contracts
from generator.models import ScenarioSpec
from generator.storage import validate_manifest_file
from generator.templates import evaluate_verifier, render_scenario


MIGRATED_FAULT_TEMPLATES = {
    "container_stopped", "dns_nameserver", "bird_wrong_asn",
    "random_complex_transit_acl", "random_complex_dual_bgp_acl",
    "netem_impairment", "ipv6_connected_route", "dual_bgp_ospf",
    "dual_dns_network", "cascading_network_bgp",
}


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
        self._fault_execution_id = f"{suite_id}_{spec.fingerprint[:16]}"
        self._fault_journal_path = None

    def compiled_fault_plan(self):
        if self.generated_spec.template_id not in MIGRATED_FAULT_TEMPLATES:
            return None
        from generator.faults.adapters import compile_template_faults

        topology_fingerprint = "legacy-audited-topology"
        if self.generated_spec.topology.startswith("DECLARATIVE_"):
            from generator.topology.bindings import load_capability_manifest
            from generator.topology.registry import topology_id_from_name

            capabilities = load_capability_manifest(
                topology_id_from_name(self.generated_spec.topology)
            )
            topology_fingerprint = str(capabilities["topology_fingerprint"])
        return compile_template_faults(
            self.generated_spec.template_id,
            self.generated_spec.parameters,
            topology_fingerprint=topology_fingerprint,
        )

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

    def inject_fault(self):
        """Inject and prove every generated component before scoring starts."""
        rendered = render_scenario(self.generated_spec)
        plan = self.get_compiled_fault_plan()
        if plan is None and not rendered.components:
            return BaseScenario.inject_fault(self)
        from scenarios.base import run, run_with_status

        if not self._healthy_baseline_prepared:
            self.prepare_healthy_baseline()
        print(
            f"  注入组合故障: {self.fault_type} "
            f"({len(rendered.components)} components)"
        )
        try:
            if plan is not None:
                from generator.faults.journal import FaultExecutor

                executor = FaultExecutor(
                    Path(__file__).resolve().parents[1] / "generated" / "fault-journal"
                )
                self._fault_journal_path = executor.inject(
                    plan, self._fault_execution_id
                )
            else:
                for component in sorted(
                    rendered.components,
                    key=lambda item: item.inject_order,
                ):
                    returncode, output = run_with_status(
                        component.inject_command,
                        timeout=120,
                    )
                    if returncode != 0:
                        raise RuntimeError(
                            f"component {component.component_id} injection failed "
                            f"(exit={returncode}):\n{output[:2000]}"
                        )
                    check_code, check_output = run_with_status(
                        component.fault_check_command,
                        timeout=30,
                    )
                    if check_code != 0 or not evaluate_verifier(
                        component.fault_verifier_kind,
                        component.fault_verifier_value,
                        check_output,
                    ):
                        raise RuntimeError(
                            f"component {component.component_id} did not become active:\n"
                            f"{check_output[:2000]}"
                        )
            time.sleep(self.fault_settle_seconds)
            fault_output = run(self.get_verify_cmd(), timeout=30)
            if not self.check_fault_active(fault_output):
                raise RuntimeError(
                    "all components were present but aggregate functional impact "
                    f"was absent:\n{fault_output[:2000]}"
                )
        except Exception:
            self.execute_standard_cleanup(timeout=120)
            self._healthy_baseline_prepared = False
            raise
        self._healthy_baseline_prepared = False
        print("  组合故障验证成功")

    def execute_standard_cleanup(self, timeout=90):
        from scenarios.base import run

        plan = self.get_compiled_fault_plan()
        if plan is not None and self._fault_journal_path is not None:
            from generator.faults.journal import FaultExecutor

            executor = FaultExecutor(
                Path(__file__).resolve().parents[1] / "generated" / "fault-journal"
            )
            path = executor.recover(plan, self._fault_execution_id)
            self._fault_journal_path = None
            return f"fault journal recovered: {path}"
        return run(self.get_fix_cmd(), timeout=timeout)

    expected_roots = tuple(
        {
            "category": root.category,
            "target_container": list(root.target_container),
            "artifact": root.artifact,
            "faulty_value": root.faulty_value,
            "expected_value": root.expected_value,
        }
        for root in spec.expected_root_causes
    ) or (
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
        "inject_fault": inject_fault,
        "execute_standard_cleanup": execute_standard_cleanup,
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
        "fault_relationship": spec.fault_relationship,
        "fault_components": spec.fault_components,
        "causal_chain": spec.causal_chain,
        "generated_suite_id": suite_id,
        "generation_fingerprint": spec.fingerprint,
        "generation_contract_sha256": contract_sha256,
        "get_compiled_fault_plan": compiled_fault_plan,
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
        if any(spec.main_score_eligible for spec in manifest.scenarios):
            from generator.promotion import verify_promotion_record

            verify_promotion_record(root, manifest)
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
