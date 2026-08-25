"""Compile validated topology plans with SEED Emulator and publish capabilities."""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import shlex
from typing import Dict

import yaml

from generator.topology.models import TopologyPlan
from generator.topology.planner import validate_topology_plan
from generator.topology.registry import output_dir
from generator.software import (
    BUILTIN_ROUTER_SOFTWARE,
    SOFTWARE_SPEC_VERSION,
    capability_entry,
    node_matches,
    resolved_packages,
)


def _software_specs(plan: TopologyPlan):
    from generator.topology.models import TopologyRequest

    request = TopologyRequest.from_dict(plan.request)
    return (BUILTIN_ROUTER_SOFTWARE, *request.software)


def _apply_software(node, plan: TopologyPlan, *, role: str, asn: int, node_name: str):
    """Translate SoftwareSpec data into SEED node APIs, never raw user shell."""
    applied = []
    for spec in _software_specs(plan):
        if not node_matches(spec, role=role, asn=asn, node_name=node_name):
            continue
        for package in resolved_packages(spec):
            node.addSoftware(package)
        for managed in spec.managed_files:
            node.setFile(managed.path, managed.content)
            node.addBuildCommandAtEnd(
                f"chmod {managed.mode} {shlex.quote(managed.path)}"
            )
        applied.append(spec)
    return tuple(applied)


def build_emulator(plan: TopologyPlan):
    validate_topology_plan(plan)
    from seedemu.core import Emulator
    from seedemu.layers import Base, Ebgp, Ospf, PeerRelationship, Routing

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
        # A deterministic, documentation-prefix IPv6 connected route is a
        # bounded topology fixture for the audited route-removal FaultDriver.
        # It is not attached to a Docker network and cannot reach the host.
        ipv6_address = f"2001:db8:{item.index:x}::1/64"
        router.appendStartCommand(
            "ip link show benchmark6 >/dev/null 2>&1 || "
            "ip link add benchmark6 type dummy"
        )
        router.appendStartCommand("ip link set benchmark6 up")
        router.appendStartCommand(
            f"ip -6 addr replace {ipv6_address} dev benchmark6"
        )
        _apply_software(
            router, plan, role="router", asn=item.asn, node_name="router0"
        )
        for index, address in enumerate(item.host_addresses):
            node_name = f"host{index}"
            host = autonomous_system.createHost(node_name)
            host.joinNetwork("lan0", address)
            _apply_software(
                host, plan, role="host", asn=item.asn, node_name=node_name
            )
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
    # OSPF emits a real BIRD `area 0` contract. Even a single-router AS gets a
    # passive LAN stanza, which is enough for deterministic config mutation
    # without fabricating runtime capabilities in the Bundle layer.
    for layer in (base, Routing(), Ospf(), ebgp):
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
        normalized_role = "router" if "Router" in role else "host"
        software = [
            capability_entry(
                spec,
                source="builtin" if spec is BUILTIN_ROUTER_SOFTWARE else "declared",
            )
            for spec in _software_specs(plan)
            if node_matches(
                spec,
                role=normalized_role,
                asn=int(labels["org.seedsecuritylabs.seedemu.meta.asn"]),
                node_name=labels.get("org.seedsecuritylabs.seedemu.meta.nodename", ""),
            )
        ]
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
            "software": software,
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
        "netem": [
            {"container": item["container"], "asn": item["asn"], "interface": "lan0"}
            for item in assets
            if any(iface["name"] == "lan0" for iface in item["interfaces"])
        ],
        "ipv6_connected_route": [
            {
                "container": item["container"],
                "interface": "benchmark6",
                "address": f"2001:db8:{index:x}::1/64",
                "prefix": str(ipaddress.ip_network(
                    f"2001:db8:{index:x}::1/64", strict=False
                )),
            }
            for index, item in enumerate(routers)
        ],
        "bird_ospf_wrong_area": [
            {"container": item["container"], "correct_area": 0}
            for item in routers
        ],
        "docker_network_disconnected": [],
        "software_fault_profiles": [],
    }
    project = str(compose.get("name", f"decl_{plan.topology_id}"))
    by_service = {
        str(item["service"]): item for item in assets
    }
    for service_name, service in sorted((compose.get("services") or {}).items()):
        asset = by_service.get(str(service_name))
        if not asset:
            continue
        for network_key, attachment in sorted((service.get("networks") or {}).items()):
            attachment = attachment or {}
            target_ip = str(attachment.get("ipv4_address", ""))
            interface = next((
                item["name"] for item in asset["interfaces"]
                if str(item["address"]).split("/")[0] == target_ip
            ), "")
            if not interface or not target_ip:
                continue
            target_interface = ipaddress.ip_interface(next(
                item["address"] for item in asset["interfaces"]
                if item["name"] == interface
            ))
            peers = []
            for candidate in assets:
                if candidate["container"] == asset["container"]:
                    continue
                for candidate_interface in candidate["interfaces"]:
                    if candidate_interface["name"] != interface:
                        continue
                    parsed = ipaddress.ip_interface(candidate_interface["address"])
                    if parsed.network == target_interface.network:
                        peers.append((candidate, str(parsed.ip)))
            if not peers:
                continue
            peers.sort(key=lambda item: (
                item[0]["asn"] == asset["asn"], item[0]["container"]
            ))
            peer, peer_ip = peers[0]
            bindings["docker_network_disconnected"].append({
                "container": asset["container"],
                "docker_network": f"{project}_{network_key}",
                "interface": interface,
                "target_ip": target_ip,
                "peer_container": peer["container"],
                "peer_ip": peer_ip,
                "remove_interface": False,
                "bird_reconfigure": "Router" in str(asset["role"]),
            })
    for asset in assets:
        for software in asset.get("software") or ():
            for profile in software.get("fault_profiles") or ():
                bindings["software_fault_profiles"].append({
                    "container": asset["container"],
                    "software_id": software["software_id"],
                    "profile_id": profile["profile_id"],
                    "fault_type": profile["fault_type"],
                    "parameters": dict(profile["parameters"]),
                })
    return {
        "schema_version": 1,
        "software_capability_schema_version": SOFTWARE_SPEC_VERSION,
        "topology_id": plan.topology_id,
        "topology_name": plan.topology_name,
        "compose_project": project,
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
        "software_catalog": [
            capability_entry(
                spec,
                source="builtin" if spec is BUILTIN_ROUTER_SOFTWARE else "declared",
            )
            for spec in _software_specs(plan)
        ],
        "fault_component_bindings": bindings,
    }


def compile_topology(
    plan: TopologyPlan, *, override: bool = True, root: Path | None = None,
) -> Path:
    from seedemu.compiler import Docker, Platform

    destination = output_dir(plan.topology_id, root) if root is not None else output_dir(plan.topology_id)
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


def validate_compiled_output(
    plan: TopologyPlan, *, root: Path | None = None,
) -> Dict[str, object]:
    destination = output_dir(plan.topology_id, root) if root is not None else output_dir(plan.topology_id)
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
    for component in (
        "ipv6_connected_route", "bird_ospf_wrong_area",
        "docker_network_disconnected",
    ):
        if not manifest["fault_component_bindings"].get(component):
            raise ValueError(f"compiled topology exposes no {component} bindings")
    if "software_catalog" in manifest:
        expected_catalog = [
            capability_entry(
                spec,
                source="builtin" if spec is BUILTIN_ROUTER_SOFTWARE else "declared",
            )
            for spec in _software_specs(plan)
        ]
        if (
            manifest.get("software_capability_schema_version") != SOFTWARE_SPEC_VERSION
            or manifest["software_catalog"] != expected_catalog
        ):
            raise ValueError("compiled software capability catalog differs from plan")
        for asset in manifest["assets"]:
            normalized_role = "router" if "Router" in asset["role"] else "host"
            expected = [
                entry for spec, entry in zip(_software_specs(plan), expected_catalog)
                if node_matches(
                    spec, role=normalized_role, asn=int(asset["asn"]),
                    node_name=asset["node_name"],
                )
            ]
            if asset.get("software") != expected:
                raise ValueError("compiled asset software capabilities differ from plan")
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
