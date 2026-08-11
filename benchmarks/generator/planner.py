"""Deterministic scenario planning with semantic deduplication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, List, Set

from generator.models import (
    FaultComponentSpec,
    GenerationJob,
    RootCauseSpec,
    ScenarioSpec,
    SuiteManifest,
    VALID_TRACKS,
    scenario_fingerprint,
)
from generator.templates import TEMPLATES, get_template


SUITE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def validate_job(job: GenerationJob) -> None:
    if not SUITE_ID_PATTERN.fullmatch(job.suite_id):
        raise ValueError(
            "suite_id must be 3-64 lowercase snake_case characters"
        )
    if not 1 <= job.case_count <= 10000:
        raise ValueError("case_count must be between 1 and 10000")
    if not job.master_seed:
        raise ValueError("master_seed must not be empty")
    if job.benchmark_track not in VALID_TRACKS:
        raise ValueError(
            f"unsupported benchmark_track={job.benchmark_track}"
        )
    for template_id in job.template_ids:
        get_template(template_id)
    if job.topology and not any(
        item.topology == job.topology for item in TEMPLATES.values()
    ):
        raise ValueError(f"no audited templates for topology={job.topology}")


def _seed_number(master_seed: str) -> int:
    digest = hashlib.sha256(master_seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _existing_fingerprints(
    benchmarks_dir: Path,
    *,
    excluding_suite: str,
) -> Set[str]:
    fingerprints: Set[str] = set()
    specs_dir = benchmarks_dir / "specs"
    if not specs_dir.is_dir():
        return fingerprints
    for path in specs_dir.glob("*/manifest.json"):
        if path.parent.name == excluding_suite:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in value.get("scenarios", []):
            fingerprint = item.get("fingerprint")
            if isinstance(fingerprint, str) and fingerprint:
                fingerprints.add(fingerprint)
    return fingerprints


def plan_suite(
    job: GenerationJob,
    *,
    contract_sha256: str,
    benchmarks_dir: Path,
) -> SuiteManifest:
    validate_job(job)
    if job.template_ids:
        selected_ids = list(job.template_ids)
    elif job.topology:
        selected_ids = [
            key
            for key, value in sorted(TEMPLATES.items())
            if value.topology == job.topology
        ]
    else:
        selected_ids = [
            key
            for key, value in sorted(TEMPLATES.items())
            if value.default_enabled
        ]
    if job.topology:
        selected_ids = [
            item
            for item in selected_ids
            if get_template(item).topology == job.topology
        ]
    if not selected_ids:
        raise ValueError("generation job selected no fault templates")

    seed = _seed_number(job.master_seed)
    rotation = seed % len(selected_ids)
    selected_ids = selected_ids[rotation:] + selected_ids[:rotation]
    counters = {template_id: 0 for template_id in selected_ids}
    fingerprints = _existing_fingerprints(
        benchmarks_dir,
        excluding_suite=job.suite_id,
    )
    scenarios: List[ScenarioSpec] = []
    attempts = 0
    max_attempts = max(1000, job.case_count * 100)

    while len(scenarios) < job.case_count and attempts < max_attempts:
        template_id = selected_ids[attempts % len(selected_ids)]
        template = get_template(template_id)
        sequence = counters[template_id]
        counters[template_id] += 1
        attempts += 1
        parameters = template.candidate(sequence, seed)
        fingerprint = scenario_fingerprint(
            template_id,
            template.topology,
            parameters,
        )
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        targets, artifact, faulty, expected = template.diagnosis(parameters)
        rendered = template.renderer(parameters)
        if rendered.components:
            expected_root_causes = tuple(
                RootCauseSpec(
                    category=component.category,
                    target_container=component.target_containers,
                    artifact=component.artifact,
                    faulty_value=component.faulty_value,
                    expected_value=component.expected_value,
                )
                for component in rendered.components
            )
            fault_components = tuple(
                FaultComponentSpec(
                    component_id=component.component_id,
                    category=component.category,
                    target_containers=component.target_containers,
                    artifact=component.artifact,
                    inject_order=component.inject_order,
                    cleanup_order=component.cleanup_order,
                    depends_on=component.depends_on,
                )
                for component in rendered.components
            )
            repair_containers = tuple(
                dict.fromkeys(
                    target
                    for component in rendered.components
                    for target in component.target_containers
                )
            )
        else:
            expected_root_causes = (
                RootCauseSpec(
                    category=template.fault_type,
                    target_container=targets,
                    artifact=artifact,
                    faulty_value=faulty,
                    expected_value=expected,
                ),
            )
            fault_components = ()
            repair_containers = targets
        scenario_seed = int.from_bytes(
            hashlib.sha256(
                f"{job.master_seed}:{fingerprint}".encode("utf-8")
            ).digest()[:8],
            "big",
        )
        timeout = {
            "bird_wrong_asn": 120,
            "dual_bgp_ospf": 150,
            "dual_dns_network": 90,
            "cascading_network_bgp": 150,
            "random_complex_transit_acl": 240,
            "random_complex_dual_bgp_acl": 300,
        }.get(template_id, 60)
        scenarios.append(
            ScenarioSpec(
                name=f"gen_{template_id}_{fingerprint[:10]}_01",
                description=(
                    f"Generated deterministic case: {template.description}"
                ),
                topology=template.topology,
                fault_type=template.fault_type,
                template_id=template_id,
                parameters=parameters,
                diagnosis_targets=targets,
                diagnosis_artifact=artifact,
                diagnosis_faulty_value=faulty,
                diagnosis_expected_value=expected,
                benchmark_track=job.benchmark_track,
                difficulty=template.difficulty,
                main_score_eligible=False,
                quarantine_reason=(
                    f"generated suite {job.suite_id}; promote only after live validation"
                ),
                repair_containers=repair_containers,
                scenario_seed=scenario_seed,
                fingerprint=fingerprint,
                convergence_timeout=timeout,
                fault_settle_seconds=3,
                fault_relationship=template.fault_relationship,
                expected_root_causes=expected_root_causes,
                fault_components=fault_components,
                causal_chain=template.causal_chain(parameters),
            )
        )

    if len(scenarios) != job.case_count:
        raise ValueError(
            f"only planned {len(scenarios)}/{job.case_count} unique scenarios"
        )
    return SuiteManifest(
        suite_id=job.suite_id,
        master_seed=job.master_seed,
        contract_sha256=contract_sha256,
        scenarios=tuple(scenarios),
        enabled=job.enabled,
    )
