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
)
TEMPLATE_COMPONENTS = {
    "container_stopped": "container_stopped",
    "dns_nameserver": "dns_nameserver",
    "bird_wrong_asn": "bird_wrong_asn",
    "random_complex_transit_acl": "scoped_acl",
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
    if component_id == "container_stopped":
        candidates = list(bindings.get(component_id) or [])
        if not candidates:
            raise ValueError("topology has no host container binding")
        return {"container": candidates[(sequence + seed) % len(candidates)]}
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
    if component_id == "container_stopped":
        if set(parameters) != {"container"} or parameters.get("container") not in (
            bindings.get(component_id) or []
        ):
            raise ValueError("container stop target is outside topology capabilities")
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
