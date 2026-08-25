"""Bind existing audited fault primitives to compiled declarative assets."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from generator.topology.registry import load_plan, output_dir


SUPPORTED_COMPONENTS = (
    "container_stopped",
    "dns_nameserver",
    "bird_wrong_asn",
    "scoped_acl",
    "netem",
    "bird_wrong_asn_scoped_acl",
    "ipv6_connected_route",
    "bird_ospf_wrong_area",
    "docker_network_disconnected",
    "software_config_replace",
    "software_executable_disabled",
)
TEMPLATE_COMPONENTS = {
    "container_stopped": "container_stopped",
    "dns_nameserver": "dns_nameserver",
    "bird_wrong_asn": "bird_wrong_asn",
    "random_complex_transit_acl": "scoped_acl",
    "random_complex_dual_bgp_acl": "bird_wrong_asn_scoped_acl",
    "netem_impairment": "netem",
    "ipv6_connected_route": "ipv6_connected_route",
}


def load_capability_manifest(topology_id: str) -> Dict[str, Any]:
    plan = load_plan(topology_id)
    path = output_dir(topology_id) / "topology_manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("topology_fingerprint") != plan.fingerprint:
        raise ValueError("fault bindings target a stale topology build")
    return value


def bind_fault_component(
    manifest: Mapping[str, Any],
    component_id: str,
    sequence: int,
    master_seed: str,
) -> Dict[str, Any]:
    """Return concrete parameters without changing existing safety semantics."""
    if component_id not in SUPPORTED_COMPONENTS:
        raise ValueError(f"unsupported topology fault component={component_id}")
    if sequence < 0:
        raise ValueError("component sequence must be non-negative")
    bindings = manifest.get("fault_component_bindings") or {}
    seed = int.from_bytes(
        hashlib.sha256(master_seed.encode("utf-8")).digest()[:8], "big"
    )
    assets = list(manifest.get("assets") or [])
    if component_id == "bird_wrong_asn_scoped_acl":
        acl = bind_fault_component(manifest, "scoped_acl", sequence, master_seed)
        bad_asn = 64512 + ((sequence + seed) % 1023)
        if bad_asn == acl["source_asn"]:
            bad_asn = 64512 + ((bad_asn - 64512 + 1) % 1023)
        return {
            **acl,
            "template_revision": 2,
            "correct_asn": acl["source_asn"],
            "bad_asn": bad_asn,
            # Declarative edges compile as PeerRelationship.Unfiltered, whose
            # SEED/BIRD protocol prefix is ``x_`` (commercial peers use p_).
            "peer_protocol": f"x_as{acl['destination_asn']}",
        }
    if component_id in {
        "ipv6_connected_route", "docker_network_disconnected",
    }:
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError(f"topology has no {component_id} binding")
        return dict(candidates[(sequence + seed) % len(candidates)])
    if component_id == "bird_ospf_wrong_area":
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError("topology has no BIRD OSPF binding")
        selected = dict(candidates[(sequence + seed) % len(candidates)])
        bad_area = 1 + ((sequence + seed) % 65534)
        if bad_area == int(selected["correct_area"]):
            bad_area += 1
        return {**selected, "bad_area": bad_area}
    if component_id in {
        "software_config_replace", "software_executable_disabled",
    }:
        fault_type = {
            "software_config_replace": "software.config.replace",
            "software_executable_disabled": "software.executable.disabled",
        }[component_id]
        candidates = [
            item for item in bindings.get("software_fault_profiles") or ()
            if item.get("fault_type") == fault_type
        ]
        if not candidates:
            raise ValueError(f"topology has no {fault_type} profile binding")
        return dict(candidates[(sequence + seed) % len(candidates)])
    if component_id == "container_stopped":
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError("topology has no host container binding")
        return {"container": candidates[(sequence + seed) % len(candidates)]}
    if component_id == "netem":
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError("capability manifest has no netem targets")
        selected = candidates[(sequence + seed) % len(candidates)]
        peer_candidates = [
            item for item in assets
            if item.get("asn") == selected.get("asn")
            and item.get("container") != selected.get("container")
        ]
        if not peer_candidates:
            raise ValueError("netem target has no same-AS probe peer")
        peer = peer_candidates[sequence % len(peer_candidates)]
        peer_lan = next(
            item["address"].split("/")[0]
            for item in peer.get("interfaces", []) if item["name"] == "lan0"
        )
        profiles = (
            {"delay_ms": 120, "jitter_ms": 20, "loss_percent": 0, "rate_kbit": 0},
            {"delay_ms": 0, "jitter_ms": 0, "loss_percent": 25, "rate_kbit": 0},
            {"delay_ms": 0, "jitter_ms": 0, "loss_percent": 0, "rate_kbit": 256},
            {"delay_ms": 80, "jitter_ms": 30, "loss_percent": 5, "rate_kbit": 512},
        )
        return {
            "container": selected["container"],
            "interface": selected["interface"],
            "peer_container": peer["container"],
            "peer_ip": peer_lan,
            **profiles[sequence % len(profiles)],
        }
    if component_id == "bird_wrong_asn":
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError("topology has no BIRD router binding")
        selected = dict(candidates[(sequence + seed) % len(candidates)])
        bad_asn = 64512 + ((sequence + seed) % 1023)
        if bad_asn == selected["correct_asn"]:
            bad_asn = 64512 + ((bad_asn - 64512 + 1) % 1023)
        return {**selected, "bad_asn": bad_asn}
    if component_id == "dns_nameserver":
        hosts = [item for item in assets if item.get("role") == "Host"]
        if not hosts:
            raise ValueError("topology has no DNS-capable host binding")
        host = hosts[(sequence + seed) % len(hosts)]
        routers = [
            item
            for item in assets
            if "Router" in item.get("role", "") and item.get("asn") == host.get("asn")
        ]
        if not routers:
            raise ValueError("host AS has no router for DNS reachability verification")
        router = routers[0]
        peer_ip = next(
            iface["address"].split("/")[0]
            for iface in router["interfaces"]
            if iface["name"] == "lan0"
        )
        documentation = ("192.0.2", "198.51.100", "203.0.113")
        return {
            "container": host["container"],
            "peer_container": router["container"],
            "peer_ip": peer_ip,
            "bad_nameserver": f"{documentation[(sequence + seed) % 3]}.{1 + (sequence % 253)}",
            "expected_nameserver": "127.0.0.11",
        }
    candidates = list(bindings.get("scoped_acl") or [])
    if not candidates:
        raise ValueError("topology has no IX-facing ACL binding")
    selected = candidates[(sequence + seed) % len(candidates)]
    interface = selected["interfaces"][sequence % len(selected["interfaces"])]
    source_interface = ipaddress.ip_interface(interface["address"])
    peers = []
    for asset in assets:
        if asset["container"] == selected["container"]:
            continue
        for candidate_interface in asset["interfaces"]:
            if candidate_interface["name"] != interface["name"]:
                continue
            peer_interface = ipaddress.ip_interface(candidate_interface["address"])
            if peer_interface.network == source_interface.network:
                peers.append((asset, peer_interface))
    if not peers:
        raise ValueError("IX binding has no peer endpoint")
    peer, peer_interface = peers[sequence % len(peers)]
    return {
        "topology_seed": 20260724,
        "source_asn": selected["asn"],
        "destination_asn": peer["asn"],
        "source_router": selected["container"],
        "source_interface": interface["name"],
        "source_ip": str(source_interface.ip),
        "destination_container": peer["container"],
        "destination_ip": str(peer_interface.ip),
        "probe_size": (56, 120, 256, 512)[sequence % 4],
        "rule_comment": "SEED_RANDOM_COMPLEX_ACL",
    }


def validate_fault_binding(
    manifest: Mapping[str, Any], component_id: str, parameters: Mapping[str, Any]
) -> None:
    """Prove rendered parameters remain inside compiled topology capabilities."""
    assets = list(manifest.get("assets") or [])
    bindings = manifest.get("fault_component_bindings") or {}
    if component_id == "bird_wrong_asn_scoped_acl":
        required_extra = {
            "template_revision", "correct_asn", "bad_asn", "peer_protocol"
        }
        if not required_extra.issubset(parameters):
            raise ValueError("invalid compound BIRD/ACL binding keys")
        acl = {key: value for key, value in parameters.items() if key not in required_extra}
        validate_fault_binding(manifest, "scoped_acl", acl)
        if (
            int(parameters.get("template_revision", -1)) != 2
            or int(parameters.get("correct_asn", -1)) != int(parameters["source_asn"])
            or int(parameters.get("bad_asn", -1)) == int(parameters["source_asn"])
            or not 64512 <= int(parameters.get("bad_asn", -1)) <= 65534
            or parameters.get("peer_protocol") != f"x_as{parameters['destination_asn']}"
        ):
            raise ValueError("compound BIRD/ACL binding differs from capabilities")
        return
    if component_id == "ipv6_connected_route":
        candidates = list(bindings.get(component_id) or ())
        if dict(parameters) not in candidates:
            raise ValueError("IPv6 route binding differs from compiled topology")
        address = ipaddress.ip_interface(str(parameters.get("address")))
        prefix = ipaddress.ip_network(str(parameters.get("prefix")))
        if (
            address.version != 6 or prefix.version != 6
            or address.network != prefix
            or parameters.get("interface") != "benchmark6"
        ):
            raise ValueError("invalid IPv6 connected-route binding")
        return
    if component_id == "bird_ospf_wrong_area":
        if set(parameters) != {"container", "correct_area", "bad_area"}:
            raise ValueError("invalid BIRD OSPF binding keys")
        expected = {
            item["container"]: int(item["correct_area"])
            for item in bindings.get(component_id) or ()
        }
        correct = int(parameters.get("correct_area", -1))
        bad = int(parameters.get("bad_area", -1))
        if expected.get(parameters.get("container")) != correct or bad < 0 or bad == correct:
            raise ValueError("BIRD OSPF binding differs from compiled topology")
        return
    if component_id == "docker_network_disconnected":
        candidates = list(bindings.get(component_id) or ())
        if dict(parameters) not in candidates:
            raise ValueError("Docker network binding differs from compiled topology")
        ipaddress.ip_address(str(parameters.get("target_ip")))
        ipaddress.ip_address(str(parameters.get("peer_ip")))
        by_container = {item["container"]: item for item in assets}
        if parameters.get("peer_container") not in by_container:
            raise ValueError("Docker network semantic peer is outside topology")
        project = str(
            (manifest.get("runtime_session") or {}).get("compose_project")
            or manifest.get("compose_project", "")
        )
        if not project or not str(parameters.get("docker_network", "")).startswith(
            f"{project}_"
        ):
            raise ValueError("Docker network binding lacks scoped project identity")
        return
    if component_id in {
        "software_config_replace", "software_executable_disabled",
    }:
        fault_type = {
            "software_config_replace": "software.config.replace",
            "software_executable_disabled": "software.executable.disabled",
        }[component_id]
        candidates = [
            dict(item) for item in bindings.get("software_fault_profiles") or ()
            if item.get("fault_type") == fault_type
        ]
        if dict(parameters) not in candidates:
            raise ValueError("software profile binding differs from compiled topology")
        return
    if component_id == "container_stopped":
        if set(parameters) != {"container"} or parameters.get("container") not in (
            bindings.get(component_id) or []
        ):
            raise ValueError("container stop target is outside topology capabilities")
        return
    if component_id == "netem":
        required = {
            "container", "interface", "peer_container", "peer_ip",
            "delay_ms", "jitter_ms", "loss_percent", "rate_kbit",
        }
        candidates = {
            (item["container"], item["interface"])
            for item in bindings.get(component_id) or []
        }
        by_container = {item["container"]: item for item in assets}
        target = by_container.get(parameters.get("container"))
        peer = by_container.get(parameters.get("peer_container"))
        peer_ips = {
            item["address"].split("/")[0]
            for item in (peer or {}).get("interfaces", []) if item["name"] == "lan0"
        }
        delay = int(parameters.get("delay_ms", -1))
        jitter = int(parameters.get("jitter_ms", -1))
        loss = float(parameters.get("loss_percent", -1))
        rate = int(parameters.get("rate_kbit", -1))
        if (
            set(parameters) != required
            or (parameters.get("container"), parameters.get("interface")) not in candidates
            or not target or not peer or target.get("asn") != peer.get("asn")
            or parameters.get("peer_ip") not in peer_ips
            or not 0 <= delay <= 5000 or not 0 <= jitter <= delay
            or not 0 <= loss <= 100 or not 0 <= rate <= 10_000_000
            or not any((delay, loss, rate))
        ):
            raise ValueError("netem binding differs from compiled topology capabilities")
        return
    if component_id == "bird_wrong_asn":
        if set(parameters) != {"container", "correct_asn", "bad_asn"}:
            raise ValueError("invalid BIRD binding keys")
        expected = {
            item["container"]: item["correct_asn"]
            for item in bindings.get(component_id) or []
        }
        container = parameters.get("container")
        correct = int(parameters.get("correct_asn", -1))
        bad = int(parameters.get("bad_asn", -1))
        if expected.get(container) != correct or bad == correct or not 64512 <= bad <= 65534:
            raise ValueError("BIRD binding differs from compiled router capabilities")
        return
    if component_id == "dns_nameserver":
        required = {
            "container", "peer_container", "peer_ip",
            "bad_nameserver", "expected_nameserver",
        }
        if set(parameters) != required:
            raise ValueError("invalid DNS binding keys")
        by_container = {item["container"]: item for item in assets}
        host = by_container.get(parameters.get("container"))
        peer = by_container.get(parameters.get("peer_container"))
        peer_lan = {
            iface["address"].split("/")[0]
            for iface in (peer or {}).get("interfaces", [])
            if iface["name"] == "lan0"
        }
        bad_ip = ipaddress.ip_address(str(parameters.get("bad_nameserver")))
        documentation = tuple(
            ipaddress.ip_network(value)
            for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
        )
        if (
            not host or host.get("role") != "Host" or not peer
            or "Router" not in peer.get("role", "")
            or host.get("asn") != peer.get("asn")
            or parameters.get("peer_ip") not in peer_lan
            or parameters.get("expected_nameserver") != "127.0.0.11"
            or not any(bad_ip in network for network in documentation)
        ):
            raise ValueError("DNS binding differs from compiled topology capabilities")
        return
    if component_id != "scoped_acl":
        raise ValueError(f"unsupported topology fault component={component_id}")
    required = {
        "topology_seed", "source_asn", "destination_asn", "source_router",
        "source_interface", "source_ip", "destination_container",
        "destination_ip", "probe_size", "rule_comment",
    }
    if set(parameters) != required:
        raise ValueError("invalid scoped ACL binding keys")
    by_container = {item["container"]: item for item in assets}
    source = by_container.get(parameters.get("source_router"))
    destination = by_container.get(parameters.get("destination_container"))
    interface = str(parameters.get("source_interface"))
    source_addresses = {
        item["address"].split("/")[0]
        for item in (source or {}).get("interfaces", [])
        if item["name"] == interface
    }
    destination_addresses = {
        item["address"].split("/")[0]
        for item in (destination or {}).get("interfaces", [])
        if item["name"] == interface
    }
    if (
        not source or not destination or source == destination
        or source.get("asn") != int(parameters.get("source_asn", -1))
        or destination.get("asn") != int(parameters.get("destination_asn", -1))
        or parameters.get("source_ip") not in source_addresses
        or parameters.get("destination_ip") not in destination_addresses
        or int(parameters.get("probe_size", -1)) not in (56, 120, 256, 512)
        or parameters.get("rule_comment") != "SEED_RANDOM_COMPLEX_ACL"
    ):
        raise ValueError("scoped ACL binding differs from compiled topology capabilities")
