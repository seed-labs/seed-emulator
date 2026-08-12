"""Static safety and compatibility gates for generated suites."""

from __future__ import annotations

import re
from typing import Iterable, List

from generator.models import (
    GENERATOR_VERSION,
    ScenarioSpec,
    SuiteManifest,
    VALID_DIFFICULTIES,
    VALID_FAULT_RELATIONSHIPS,
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
COMPONENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

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

FAULT_CHECK_MUTATION_MARKERS = (
    "sed -i",
    "sed -e",
    "iptables -a",
    "iptables -d",
    "iptables -f",
    "iptables -i",
    "iptables -p",
    "ip addr add",
    "ip addr del",
    "ip link add",
    "ip link del",
    "ip link set",
    "tc qdisc add",
    "tc qdisc del",
    "tc qdisc replace",
    "birdc configure",
    "docker start",
    "docker stop",
    "docker restart",
    "docker network connect",
    "docker network disconnect",
    "vtysh -c 'configure",
    " > ",
    " >> ",
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
    if spec.fault_relationship not in VALID_FAULT_RELATIONSHIPS:
        raise ValueError(
            f"invalid fault_relationship={spec.fault_relationship}"
        )
    if spec.main_score_eligible:
        if spec.benchmark_track not in {
            "network_functional", "network_control_plane"
        }:
            raise ValueError("promoted scenario uses a non-scoring track")
        if spec.quarantine_reason.strip():
            raise ValueError("promoted scenario must clear quarantine reason")
    elif not spec.quarantine_reason.strip():
        raise ValueError("quarantined generated scenario requires a reason")
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
    if template.topology != spec.topology and not spec.topology.startswith(
        "DECLARATIVE_"
    ):
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
    if not spec.expected_root_causes:
        raise ValueError("generated scenario requires expected_root_causes")
    for root in spec.expected_root_causes:
        if not all(
            str(value).strip()
            for value in (
                root.category,
                root.artifact,
                root.faulty_value,
                root.expected_value,
            )
        ):
            raise ValueError("generated root cause fields must be complete")
        if not root.target_container:
            raise ValueError("generated root cause requires target containers")
        if any(
            target not in spec.repair_containers
            for target in root.target_container
        ):
            raise ValueError("root cause escapes scenario repair scope")
    if spec.fault_type == "multiple_faults":
        if len(spec.expected_root_causes) < 2:
            raise ValueError("multiple_faults requires at least two root causes")
    elif len(spec.expected_root_causes) != 1:
        raise ValueError("single-root fault type cannot declare multiple roots")
    if spec.fault_relationship == "cascading":
        if len(spec.expected_root_causes) != 1:
            raise ValueError("cascading scenario must retain one primary root cause")
        if len(spec.causal_chain) < 2:
            raise ValueError("cascading scenario requires a causal chain")
    elif spec.causal_chain:
        raise ValueError("only cascading scenarios may declare a causal chain")

    if bool(spec.fault_components) != bool(rendered.components):
        raise ValueError("rendered and declared fault components differ")
    if spec.fault_components:
        count = len(spec.fault_components)
        component_ids = [item.component_id for item in spec.fault_components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("fault component ids must be unique")
        if any(not COMPONENT_ID_PATTERN.fullmatch(item) for item in component_ids):
            raise ValueError("invalid fault component id")
        inject_orders = {item.inject_order for item in spec.fault_components}
        cleanup_orders = {item.cleanup_order for item in spec.fault_components}
        if inject_orders != set(range(count)):
            raise ValueError("fault component inject_order must be contiguous")
        if cleanup_orders != set(range(count)):
            raise ValueError("fault component cleanup_order must be contiguous")
        if any(
            item.inject_order + item.cleanup_order != count - 1
            for item in spec.fault_components
        ):
            raise ValueError("cleanup order must reverse injection order")
        by_id = {item.component_id: item for item in spec.fault_components}
        for item in spec.fault_components:
            if not item.target_containers:
                raise ValueError("fault component has no mutation target")
            if any(
                target not in spec.repair_containers
                for target in item.target_containers
            ):
                raise ValueError("fault component escapes repair scope")
            for dependency in item.depends_on:
                if dependency not in by_id:
                    raise ValueError("fault component dependency is unknown")
                if by_id[dependency].inject_order >= item.inject_order:
                    raise ValueError("fault component dependency order is invalid")
        component_target_union = tuple(
            dict.fromkeys(
                target
                for item in sorted(
                    spec.fault_components,
                    key=lambda component: component.inject_order,
                )
                for target in item.target_containers
            )
        )
        if set(component_target_union) != set(spec.repair_containers):
            raise ValueError("repair scope must equal fault component target union")
        declared_roots = {
            (
                item.category,
                tuple(item.target_container),
                item.artifact,
                item.faulty_value,
                item.expected_value,
            )
            for item in spec.expected_root_causes
        }
        component_roots = {
            (
                item.category,
                tuple(item.target_containers),
                item.artifact,
                item.faulty_value,
                item.expected_value,
            )
            for item in rendered.components
        }
        if declared_roots != component_roots:
            raise ValueError("component metadata differs from expected root causes")
        declared_components = {
            (
                item.component_id,
                item.category,
                tuple(item.target_containers),
                item.artifact,
                item.inject_order,
                item.cleanup_order,
                tuple(item.depends_on),
            )
            for item in spec.fault_components
        }
        rendered_components = {
            (
                item.component_id,
                item.category,
                tuple(item.target_containers),
                item.artifact,
                item.inject_order,
                item.cleanup_order,
                tuple(item.depends_on),
            )
            for item in rendered.components
        }
        if declared_components != rendered_components:
            raise ValueError("rendered component contract differs from manifest")
        expected_inject = " && ".join(
            item.inject_command
            for item in sorted(
                rendered.components,
                key=lambda component: component.inject_order,
            )
        )
        expected_cleanup = "; ".join(
            item.cleanup_command
            for item in sorted(
                rendered.components,
                key=lambda component: component.cleanup_order,
            )
        )
        if rendered.inject_command != expected_inject:
            raise ValueError("aggregate injection order differs from components")
        if rendered.fix_command != expected_cleanup:
            raise ValueError("aggregate cleanup order differs from components")
        for component in rendered.components:
            if any(
                not command.strip() or "\n" in command or "\r" in command
                for command in (
                    component.inject_command,
                    component.fault_check_command,
                    component.cleanup_command,
                )
            ):
                raise ValueError("component commands must be non-empty single lines")
            check_lower = component.fault_check_command.lower()
            matched = next(
                (
                    marker
                    for marker in FAULT_CHECK_MUTATION_MARKERS
                    if marker in check_lower
                ),
                None,
            )
            if matched:
                raise ValueError(
                    f"fault activation check is not read-only: {matched}"
                )
            if evaluate_verifier(
                component.fault_verifier_kind,
                component.fault_verifier_value,
                "",
            ):
                raise ValueError("empty component evidence must never be active")
            for command in (
                component.inject_command,
                component.fault_check_command,
                component.cleanup_command,
            ):
                targets = _referenced_targets(command)
                if not targets:
                    raise ValueError("component command lacks explicit Docker target")
                if any(target not in spec.repair_containers for target in targets):
                    raise ValueError("component command escapes repair scope")
    elif spec.fault_relationship != "single":
        raise ValueError("non-single scenarios require auditable fault components")

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
