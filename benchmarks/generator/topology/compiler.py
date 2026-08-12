"""Compile validated topology plans with SEED Emulator and publish capabilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import yaml

from generator.topology.models import TopologyPlan
from generator.topology.planner import validate_topology_plan
from generator.topology.registry import output_dir


def build_emulator(plan: TopologyPlan):
    validate_topology_plan(plan)
    from seedemu.core import Emulator
    from seedemu.layers import Base, Ebgp, PeerRelationship, Routing

    emulator, base, ebgp = Emulator(), Base(), Ebgp()
    for link in plan.external_links:
        base.createInternetExchange(
            link.ix_id, prefix=link.prefix, create_rs=False
        ).getPeeringLan().setDisplayName(
            f"DECL-{plan.topology_id}-IX-{link.index}"
        )
    systems = {}
    for item in plan.autonomous_systems:
        autonomous_system = base.createAutonomousSystem(item.asn)
        autonomous_system.createNetwork("lan0", prefix=item.lan_prefix)
        router = autonomous_system.createRouter("router0")
        router.setLoopbackAddress(item.loopback_address)
        router.joinNetwork("lan0", item.router_address)
        router.addSoftware("iptables")
        for index, address in enumerate(item.host_addresses):
            autonomous_system.createHost(f"host{index}").joinNetwork("lan0", address)
        systems[item.asn] = autonomous_system
    for link in plan.external_links:
        systems[link.left_asn].getRouter("router0").joinNetwork(
            f"ix{link.ix_id}", link.left_address
        )
        systems[link.right_asn].getRouter("router0").joinNetwork(
            f"ix{link.ix_id}", link.right_address
        )
        ebgp.addPrivatePeering(
            link.ix_id,
            link.left_asn,
            link.right_asn,
            # Declarative connectivity means every AS pair admitted by the
            # graph must be reachable.  A commercial Peer policy suppresses
            # third-party routes on paths longer than one edge; Unfiltered is
            # the SEED relationship that preserves graph-wide reachability.
            PeerRelationship.Unfiltered,
            aRouter="router0",
            bRouter="router0",
        )
    for layer in (base, Routing(), ebgp):
        emulator.addLayer(layer)
    return emulator


def _capability_manifest(plan: TopologyPlan, compose_file: Path) -> Dict[str, object]:
    compose = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    assets = []
    for service_name, service in sorted(compose.get("services", {}).items()):
        labels = service.get("labels") or {}
        role = labels.get("org.seedsecuritylabs.seedemu.meta.role", "")
        if not role:
            continue
        interfaces = []
        index = 0
        while f"org.seedsecuritylabs.seedemu.meta.net.{index}.name" in labels:
            interfaces.append({
                "name": labels[f"org.seedsecuritylabs.seedemu.meta.net.{index}.name"],
                "address": labels[f"org.seedsecuritylabs.seedemu.meta.net.{index}.address"],
            })
            index += 1
        assets.append({
            "service": service_name,
            "container": service.get("container_name", service_name),
            "asn": int(labels["org.seedsecuritylabs.seedemu.meta.asn"]),
            "node_name": labels.get("org.seedsecuritylabs.seedemu.meta.nodename", ""),
            "role": role,
            "loopback_address": labels.get(
                "org.seedsecuritylabs.seedemu.meta.loopback_addr"
            ),
            "interfaces": interfaces,
        })
    routers = [item for item in assets if "Router" in item["role"]]
    hosts = [item for item in assets if item["role"] == "Host"]
    dns_hosts = []
    for asn in sorted({item["asn"] for item in hosts}):
        dns_hosts.append(next(item for item in hosts if item["asn"] == asn))
    bindings = {
        "container_stopped": [item["container"] for item in hosts],
        # One deterministic sensor host per AS bounds blind DNS observation
        # cost while retaining topology-wide AS coverage.
        "dns_nameserver": [item["container"] for item in dns_hosts],
        "bird_wrong_asn": [
            {"container": item["container"], "correct_asn": item["asn"]}
            for item in routers
        ],
        "scoped_acl": [
            {
                "container": item["container"],
                "asn": item["asn"],
                "interfaces": [iface for iface in item["interfaces"] if iface["name"].startswith("ix")],
            }
            for item in routers
            if any(iface["name"].startswith("ix") for iface in item["interfaces"])
        ],
    }
    return {
        "schema_version": 1,
        "topology_id": plan.topology_id,
        "topology_name": plan.topology_name,
        "topology_fingerprint": plan.fingerprint,
        "resource_estimate": plan.resource_estimate.__dict__,
        "actual_compose_services": len(compose.get("services", {})),
        "network_gateway_modes": {
            name: (network.get("driver_opts") or {}).get(
                "com.docker.network.bridge.gateway_mode_ipv4"
            )
            for name, network in sorted((compose.get("networks") or {}).items())
        },
        "assets": assets,
        "fault_component_bindings": bindings,
    }


def compile_topology(plan: TopologyPlan, *, override: bool = True) -> Path:
    from seedemu.compiler import Docker, Platform

    destination = output_dir(plan.topology_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    emulator = build_emulator(plan)
    emulator.render()
    platform = Platform.AMD64 if plan.platform == "amd" else Platform.ARM64
    emulator.compile(
        Docker(platform=platform, internetMapEnabled=False),
        str(destination),
        override=override,
    )
    compose_file = destination / "docker-compose.yml"
    compose = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    # Give every generated project a stable identity.  Image tags produced by
    # the serial builder must be identical to those resolved by smoke/up even
    # when the output directory itself is generically named ``output``.
    compose["name"] = f"decl_{plan.topology_id}"
    for network in (compose.get("networks") or {}).values():
        network.setdefault("driver_opts", {})[
            "com.docker.network.bridge.gateway_mode_ipv4"
        ] = "nat-unprotected"
    for service in compose.get("services", {}).values():
        if service.get("container_name") == "seedemu_internet_map":
            service["container_name"] = f"seedemu_internet_map_{plan.topology_id}"
    compose_file.write_text(
        yaml.safe_dump(compose, sort_keys=False), encoding="utf-8"
    )
    manifest = _capability_manifest(plan, compose_file)
    (destination / "topology_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def validate_compiled_output(plan: TopologyPlan) -> Dict[str, object]:
    destination = output_dir(plan.topology_id)
    manifest = json.loads((destination / "topology_manifest.json").read_text(encoding="utf-8"))
    if manifest["topology_fingerprint"] != plan.fingerprint:
        raise ValueError("compiled topology fingerprint differs from registered plan")
    expected_business = plan.resource_estimate.containers - 2
    if len(manifest["assets"]) != expected_business:
        raise ValueError(
            f"compiled asset count {len(manifest['assets'])} != {expected_business}"
        )
    if manifest["actual_compose_services"] > plan.resource_estimate.containers:
        raise ValueError("compiled service count exceeds approved container budget")
    if not manifest["network_gateway_modes"] or any(
        mode != "nat-unprotected"
        for mode in manifest["network_gateway_modes"].values()
    ):
        raise ValueError("compiled networks do not permit container routing")
    if not manifest["fault_component_bindings"]["bird_wrong_asn"]:
        raise ValueError("compiled topology exposes no router fault bindings")
    if not manifest["fault_component_bindings"]["container_stopped"]:
        raise ValueError("compiled topology exposes no host fault bindings")
    planned_loopbacks = {
        item.asn: item.loopback_address for item in plan.autonomous_systems
    }
    actual_loopbacks = {
        item["asn"]: item["loopback_address"]
        for item in manifest["assets"]
        if "Router" in item["role"]
    }
    if actual_loopbacks != planned_loopbacks:
        raise ValueError("compiled router loopbacks differ from approved allocation")
    return manifest
