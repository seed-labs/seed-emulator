"""Static safety and compatibility gates for generated suites."""

from __future__ import annotations

import re
from typing import Iterable, List

from generator.models import (
    GENERATOR_VERSION,
    ScenarioSpec,
    SuiteManifest,
    VALID_DIFFICULTIES,
    VALID_TRACKS,
    scenario_fingerprint,
)
from generator.templates import (
    evaluate_verifier,
    get_template,
    render_scenario,
    validate_template_parameters,
)


SCENARIO_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_01$")
CONTAINER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

FORBIDDEN_COMMAND_MARKERS = (
    "docker rm",
    "docker kill",
    "docker compose",
    "docker-compose",
    "--privileged",
    "/var/run/docker.sock",
    "sudo ",
    "curl ",
    "wget ",
)


def _referenced_targets(command: str) -> List[str]:
    targets = re.findall(
        r"\bdocker\s+exec(?:\s+--?[A-Za-z0-9_=.-]+)*\s+([A-Za-z0-9_.-]+)",
        command,
    )
    targets += re.findall(
        r"\bdocker\s+(?:start|stop|restart)\s+([A-Za-z0-9_.-]+)",
        command,
    )
    targets += re.findall(
        r"\bdocker\s+inspect(?:\s+--format\s+\S+)?\s+([A-Za-z0-9_.-]+)",
        command,
    )
    targets += re.findall(
        r"\bdocker\s+network\s+(?:connect|disconnect)"
        r"(?:\s+--ip(?:=|\s+)\S+)?\s+\S+\s+([A-Za-z0-9_.-]+)",
        command,
    )
    return targets


def validate_scenario_spec(spec: ScenarioSpec) -> None:
    if not SCENARIO_NAME_PATTERN.fullmatch(spec.name):
        raise ValueError(f"invalid scenario name={spec.name}")
    if not spec.name.startswith("gen_"):
        raise ValueError("generated scenario names must use the gen_ namespace")
    if spec.benchmark_track not in VALID_TRACKS:
        raise ValueError(f"invalid track={spec.benchmark_track}")
    if spec.difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"invalid difficulty={spec.difficulty}")
    if spec.main_score_eligible:
        raise ValueError("generated scenarios must be quarantined before promotion")
    if not spec.quarantine_reason.strip():
        raise ValueError("generated scenario requires a quarantine reason")
    if not spec.repair_containers:
        raise ValueError("generated scenario requires a repair scope")
    if not isinstance(spec.scenario_seed, int) or spec.scenario_seed < 0:
        raise ValueError("scenario_seed must be a non-negative integer")
    if not 1 <= spec.convergence_timeout <= 600:
        raise ValueError("convergence_timeout must be between 1 and 600")
    if not 0 <= spec.fault_settle_seconds <= 60:
        raise ValueError("fault_settle_seconds must be between 0 and 60")
    if any(not CONTAINER_PATTERN.fullmatch(item) for item in spec.repair_containers):
        raise ValueError("invalid repair container name")
    if tuple(spec.diagnosis_targets) != tuple(spec.repair_containers):
        raise ValueError("diagnosis and mutation targets must match")
    if not all(
        str(value).strip()
        for value in (
            spec.diagnosis_artifact,
            spec.diagnosis_faulty_value,
            spec.diagnosis_expected_value,
        )
    ):
        raise ValueError("generated root-cause fields must be complete")
    template = get_template(spec.template_id)
    if template.topology != spec.topology:
        raise ValueError("scenario topology differs from its audited template")
    if template.fault_type != spec.fault_type:
        raise ValueError("scenario fault type differs from its audited template")
    validate_template_parameters(spec)
    expected_fingerprint = scenario_fingerprint(
        spec.template_id,
        spec.topology,
        spec.parameters,
    )
    if expected_fingerprint != spec.fingerprint:
        raise ValueError("scenario fingerprint does not match its content")

    rendered = render_scenario(spec)
    commands = {
        "inject": rendered.inject_command,
        "verify": rendered.verify_command,
        "fix": rendered.fix_command,
    }
    if any(
        not command.strip() or "\n" in command or "\r" in command
        for command in commands.values()
    ):
        raise ValueError("generated commands must be non-empty single lines")
    for command_kind, command in commands.items():
        lowered = command.lower()
        marker = next(
            (item for item in FORBIDDEN_COMMAND_MARKERS if item in lowered),
            None,
        )
        if marker:
            raise ValueError(f"forbidden command primitive: {marker}")
        targets = _referenced_targets(command)
        if not targets:
            raise ValueError("generated command has no explicit Docker target")
        if command_kind != "verify":
            outside = [
                target
                for target in targets
                if target not in spec.repair_containers
            ]
            if outside:
                raise ValueError(
                    f"generated command escapes repair scope: {outside}"
                )
    if evaluate_verifier(
        rendered.verifier_kind,
        rendered.verifier_value,
        "",
    ):
        raise ValueError("empty verifier output must never be healthy")


def validate_manifest(manifest: SuiteManifest) -> None:
    if manifest.generator_version != GENERATOR_VERSION:
        raise ValueError(
            f"unsupported generator_version={manifest.generator_version}"
        )
    if not manifest.contract_sha256:
        raise ValueError("manifest contract hash is missing")
    if not manifest.scenarios:
        raise ValueError("manifest contains no scenarios")
    names = [item.name for item in manifest.scenarios]
    fingerprints = [item.fingerprint for item in manifest.scenarios]
    if len(names) != len(set(names)):
        raise ValueError("manifest contains duplicate scenario names")
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("manifest contains semantic duplicates")
    for spec in manifest.scenarios:
        validate_scenario_spec(spec)
