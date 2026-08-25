"""Capability-bound fault profiles used by deterministic Bundle workers.

This module is the only allow-list between topology fault bindings and the
formal Bundle lifecycle. A registered FaultDriver is not automatically safe
for qualification: every profile also declares deterministic parameters and
an independently observable test contract.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from generator.topology.bindings import bind_fault_component, validate_fault_binding


BUNDLE_FAULT_COMPONENTS = {
    "container.stopped": "container_stopped",
    "dns.nameserver": "dns_nameserver",
    "routing.bird.wrong_asn": "bird_wrong_asn",
    "network.acl.scoped": "scoped_acl",
    "network.netem": "netem",
    "network.ipv6.connected_route_removed": "ipv6_connected_route",
    "routing.bird.ospf_wrong_area": "bird_ospf_wrong_area",
    "docker.network.disconnected": "docker_network_disconnected",
    "software.config.replace": "software_config_replace",
    "software.executable.disabled": "software_executable_disabled",
}


def supported_bundle_faults() -> Tuple[str, ...]:
    return tuple(sorted(BUNDLE_FAULT_COMPONENTS))


def _target(component: str, parameters: Mapping[str, Any]) -> str:
    key = "source_router" if component == "scoped_acl" else "container"
    value = str(parameters.get(key, ""))
    if not value:
        raise ValueError(f"fault component {component} produced no target")
    return value


def _preferred_is_bound(
    component: str, preferred: str, manifest: Mapping[str, Any],
) -> bool:
    bindings = manifest.get("fault_component_bindings") or {}
    values = bindings.get(component) or ()
    if component in {"container_stopped", "dns_nameserver"}:
        return preferred in values
    if component == "netem":
        return any(item.get("container") == preferred for item in values)
    return False


def _driver_parameters(component: str, value: Mapping[str, Any]) -> Dict[str, Any]:
    if component == "container_stopped":
        return {}
    if component == "dns_nameserver":
        return {
            "bad_nameserver": value["bad_nameserver"],
            "expected_nameserver": value["expected_nameserver"],
        }
    if component == "ipv6_connected_route":
        return {
            "address": value["address"], "prefix": value["prefix"],
            "interface": value["interface"],
        }
    if component == "bird_ospf_wrong_area":
        return {
            "correct_area": value["correct_area"], "bad_area": value["bad_area"],
        }
    if component == "docker_network_disconnected":
        return {
            key: value[key] for key in (
                "docker_network", "interface", "target_ip",
                "remove_interface", "bird_reconfigure",
            )
        }
    if component in {"software_config_replace", "software_executable_disabled"}:
        return {}
    if component == "bird_wrong_asn":
        return {
            "correct_asn": value["correct_asn"],
            "bad_asn": value["bad_asn"],
        }
    if component == "scoped_acl":
        return {
            "source_ip": value["source_ip"],
            "destination_ip": value["destination_ip"],
            "probe_size": value["probe_size"],
            "rule_comment": value["rule_comment"],
        }
    if component == "netem":
        # Formal qualification needs a deterministic binary outage oracle.
        # Other netem profiles remain available through direct FaultSpec use.
        return {
            "interface": value["interface"],
            "delay_ms": 0,
            "jitter_ms": 0,
            "loss_percent": 100,
            "rate_kbit": 0,
        }
    raise ValueError(f"unsupported Bundle component={component}")


def _probe(
    component: str, parameters: Mapping[str, Any], target: str,
    manifest: Mapping[str, Any],
) -> Dict[str, Any] | None:
    if component == "dns_nameserver":
        peer = str(parameters["peer_container"])
        peer = str(
            (manifest.get("runtime_session") or {})
            .get("container_services", {})
            .get(peer, peer)
        )
        return {
            "driver": "probe.hostname",
            "selector": {"container": target},
            "parameters": {
                "name": peer,
                "expected_ip": parameters["peer_ip"],
            },
            "baseline_assertion": {"kind": "contains", "value": parameters["peer_ip"]},
            "active_assertion": {"kind": "exit_code_not", "value": 0},
            "recovery_assertion": {"kind": "contains", "value": parameters["peer_ip"]},
        }
    if component == "bird_wrong_asn":
        healthy = f"as {parameters['correct_asn']};"
        faulty = f"as {parameters['bad_asn']};"
        return {
            "driver": "probe.file",
            "selector": {"container": target},
            "parameters": {"path": "/etc/bird/bird.conf"},
            "baseline_assertion": {"kind": "contains", "value": healthy},
            "active_assertion": {"kind": "contains", "value": faulty},
            "recovery_assertion": {"kind": "contains", "value": healthy},
        }
    if component == "scoped_acl":
        common = {
            "host": parameters["destination_ip"],
            "source_ip": parameters["source_ip"],
            "size": parameters["probe_size"],
            "count": 2,
        }
        return {
            "driver": "probe.icmp",
            "selector": {"container": target},
            "parameters": common,
            "baseline_assertion": {"kind": "exit_code", "value": 0},
            "active_assertion": {"kind": "exit_code_not", "value": 0},
            "recovery_assertion": {"kind": "exit_code", "value": 0},
        }
    if component == "ipv6_connected_route":
        prefix = parameters["prefix"]
        return {
            "driver": "probe.ipv6_route",
            "selector": {"container": target},
            "parameters": {"prefix": prefix},
            "baseline_assertion": {"kind": "contains", "value": prefix},
            "active_assertion": {"kind": "not_contains", "value": prefix},
            "recovery_assertion": {"kind": "contains", "value": prefix},
        }
    if component == "bird_ospf_wrong_area":
        healthy = f"area {parameters['correct_area']}"
        faulty = f"area {parameters['bad_area']}"
        return {
            "driver": "probe.file", "selector": {"container": target},
            "parameters": {"path": "/etc/bird/bird.conf"},
            "baseline_assertion": {"kind": "contains", "value": healthy},
            "active_assertion": {"kind": "contains", "value": faulty},
            "recovery_assertion": {"kind": "contains", "value": healthy},
        }
    if component == "docker_network_disconnected":
        network = parameters["docker_network"]
        return {
            "driver": "probe.docker_network_path",
            "selector": {"container": target},
            "parameters": {
                "network": network,
                "interface": parameters["interface"],
                "target_ip": parameters["target_ip"],
                "peer_ip": parameters["peer_ip"],
            },
            "baseline_assertion": {"kind": "exit_code", "value": 0},
            "active_assertion": {"kind": "exit_code_not", "value": 0},
            "recovery_assertion": {"kind": "exit_code", "value": 0},
        }
    if component == "software_config_replace":
        profile = parameters["parameters"]
        return {
            "driver": "probe.file", "selector": {"container": target},
            "parameters": {"path": profile["path"]},
            "baseline_assertion": {"kind": "contains", "value": profile["healthy_value"]},
            "active_assertion": {"kind": "contains", "value": profile["faulty_value"]},
            "recovery_assertion": {"kind": "contains", "value": profile["healthy_value"]},
        }
    if component == "software_executable_disabled":
        path = parameters["parameters"]["path"]
        return {
            "driver": "probe.executable", "selector": {"container": target},
            "parameters": {"path": path},
            "baseline_assertion": {"kind": "exit_code", "value": 0},
            "active_assertion": {"kind": "exit_code_not", "value": 0},
            "recovery_assertion": {"kind": "exit_code", "value": 0},
        }
    return None


def build_bundle_fault_candidate(
    *, fault_type: str, template_id: str, preferred_container: str,
    sequence: int, seed: str, manifest: Mapping[str, Any],
    protected_assets: Tuple[str, ...],
) -> Dict[str, Any]:
    """Resolve one Bundle fault through the topology capability manifest."""
    try:
        component = BUNDLE_FAULT_COMPONENTS[fault_type]
    except KeyError as exc:
        raise ValueError(
            f"fault has no formal Bundle profile: {fault_type}; "
            f"supported={list(supported_bundle_faults())}"
        ) from exc

    prefer = _preferred_is_bound(component, preferred_container, manifest)
    limit = max(1, len(manifest.get("assets") or ())) * 3
    selected = None
    for offset in range(limit):
        value = bind_fault_component(
            manifest, component, sequence + offset,
            f"{seed}:{template_id}:{fault_type}",
        )
        validate_fault_binding(manifest, component, value)
        target = _target(component, value)
        if target in protected_assets:
            continue
        if prefer and target != preferred_container:
            continue
        selected = (dict(value), target)
        break
    if selected is None:
        raise ValueError(
            f"no unprotected capability binding for fault={fault_type} "
            f"template={template_id}"
        )
    binding, target = selected
    breaks_application = (
        target == preferred_container
        and component in {
            "container_stopped",
            "docker_network_disconnected",
            "netem",
        }
    )
    suffix = fault_type.replace(".", "_")
    expectation = (
        f"{template_id}_availability"
        if breaks_application else f"{template_id}_{suffix}_effect"
    )
    selector = {"container": target}
    if component in {"software_config_replace", "software_executable_disabled"}:
        selector = {
            "software": binding["software_id"],
            "fault_profile": binding["profile_id"],
            "choose": 1,
        }
    return {
        "candidate_id": f"{template_id}.{fault_type}.{sequence:02d}",
        "template_id": template_id,
        "fault_type": fault_type,
        "asset": target,
        "selector": selector,
        "parameters": _driver_parameters(component, binding),
        "must_break": [expectation],
        "breaks_application": breaks_application,
        "probe": _probe(component, binding, target, manifest),
    }
