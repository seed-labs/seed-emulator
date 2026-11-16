#!/usr/bin/env python3
"""Prepare libvirt networks for the single-hypervisor KVM workflow.

Inputs:
- kvm.yaml with a dedicated management network and optional extraNetworks.

Outputs:
- Active libvirt networks matching the requested bridges.
- Optional YAML mapping of names to UUIDs for networks defined in this build.

Side effects:
- Defines a NAT management network when it does not already exist.
- Defines unnumbered L2 networks for additional VM trunk NICs.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


LIBVIRT_URI = "qemu:///system"


def loadConfig(path: Path) -> dict[str, Any]:
    """Load one KVM input mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid YAML root in {path}: expected a mapping")
    return data


def value(mapping: dict[str, Any], *names: str, default: Any = None) -> Any:
    """Return the first present camelCase or snake_case field."""
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def managementNetworkSpec(config: dict[str, Any]) -> dict[str, str]:
    """Return the requested management network fields."""
    kvm = config.get("kvm") if isinstance(config.get("kvm"), dict) else {}
    return {
        "name": str(value(kvm, "network", default="default") or "default"),
        "bridge": str(value(kvm, "networkBridge", "network_bridge", default="") or ""),
        "cidr": str(value(kvm, "networkCidr", "network_cidr", default="") or ""),
        "gateway": str(value(kvm, "networkGateway", "network_gateway", default="") or ""),
        "dhcpStart": str(value(kvm, "dhcpStart", "dhcp_start", default="") or ""),
        "dhcpEnd": str(value(kvm, "dhcpEnd", "dhcp_end", default="") or ""),
    }


def extraNetworkSpecs(config: dict[str, Any]) -> list[dict[str, str]]:
    """Return normalized L2-only networks for additional VM NICs."""
    kvm = config.get("kvm") if isinstance(config.get("kvm"), dict) else {}
    raw = value(kvm, "extraNetworks", "extra_networks", default=[]) or []
    if not isinstance(raw, list):
        raise SystemExit("kvm.extraNetworks must be a list")

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SystemExit(f"kvm.extraNetworks[{index}] must be a mapping")
        name = str(value(item, "name", "network", default="") or "").strip()
        bridge = str(value(item, "bridge", default="") or "").strip()
        if not name:
            raise SystemExit(f"kvm.extraNetworks[{index}] requires name or network")
        if not bridge:
            raise SystemExit(f"kvm.extraNetworks[{index}] requires bridge")
        if name in seen:
            raise SystemExit(f"duplicate kvm.extraNetworks name: {name}")
        seen.add(name)
        result.append({"name": name, "bridge": bridge})
    return result


def managementNetworkXml(spec: dict[str, str]) -> str:
    """Render one validated NAT management network as libvirt XML."""
    required = ("name", "bridge", "cidr", "gateway", "dhcpStart", "dhcpEnd")
    missing = [field for field in required if not spec.get(field)]
    if missing:
        raise SystemExit(
            f"management network {spec.get('name') or '<unnamed>'} is absent and "
            f"requires fields: {', '.join(missing)}"
        )

    network = ipaddress.ip_network(spec["cidr"], strict=False)
    gateway = ipaddress.ip_address(spec["gateway"])
    dhcp_start = ipaddress.ip_address(spec["dhcpStart"])
    dhcp_end = ipaddress.ip_address(spec["dhcpEnd"])
    for label, address in (
        ("gateway", gateway),
        ("dhcpStart", dhcp_start),
        ("dhcpEnd", dhcp_end),
    ):
        if address not in network:
            raise SystemExit(f"{label} {address} is outside management CIDR {network}")
    if int(dhcp_start) > int(dhcp_end):
        raise SystemExit("management dhcpStart must not be greater than dhcpEnd")

    root = ET.Element("network")
    ET.SubElement(root, "name").text = spec["name"]
    ET.SubElement(root, "forward", {"mode": "nat"})
    ET.SubElement(
        root,
        "bridge",
        {"name": spec["bridge"], "stp": "on", "delay": "0"},
    )
    ip_node = ET.SubElement(
        root,
        "ip",
        {"address": str(gateway), "netmask": str(network.netmask)},
    )
    dhcp = ET.SubElement(ip_node, "dhcp")
    ET.SubElement(
        dhcp,
        "range",
        {"start": str(dhcp_start), "end": str(dhcp_end)},
    )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def layer2NetworkXml(spec: dict[str, str]) -> str:
    """Render one unnumbered bridge network as libvirt XML."""
    root = ET.Element("network")
    ET.SubElement(root, "name").text = spec["name"]
    ET.SubElement(
        root,
        "bridge",
        {"name": spec["bridge"], "stp": "off", "delay": "0"},
    )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def virsh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one virsh command against system libvirt."""
    command = ["virsh", "-c", LIBVIRT_URI, *args]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result


def defineNetwork(xml: str) -> None:
    """Define one libvirt network from transient XML."""
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        suffix=".xml",
        delete=False,
    ) as handle:
        handle.write(xml)
        path = Path(handle.name)
    try:
        virsh("net-define", str(path))
    finally:
        path.unlink(missing_ok=True)


def actualBridge(name: str) -> str:
    """Return the bridge configured for one existing libvirt network."""
    result = virsh("net-dumpxml", name)
    root = ET.fromstring(result.stdout)
    bridge = root.find("bridge")
    return str(bridge.get("name") or "") if bridge is not None else ""


def ensureNetwork(
    spec: dict[str, str], *, management: bool, created: dict[str, str], ownership: Path | None
) -> None:
    """Start spec, using a NAT bridge if management is true.

    Record this build's new network UUID in created and the optional ownership file.
    """
    exists = virsh("net-info", spec["name"], check=False).returncode == 0
    if not exists:
        xml = managementNetworkXml(spec) if management else layer2NetworkXml(spec)
        print(f"Defining libvirt network {spec['name']} bridge={spec['bridge']}")
        defineNetwork(xml)
        created[spec["name"]] = virsh("net-uuid", spec["name"]).stdout.strip()
        if ownership is not None:
            ownership.write_text(yaml.safe_dump(created), encoding="utf-8")

    expected_bridge = spec.get("bridge", "")
    observed_bridge = actualBridge(spec["name"])
    if expected_bridge and observed_bridge != expected_bridge:
        raise SystemExit(
            f"libvirt network {spec['name']} uses bridge {observed_bridge or '<none>'}, "
            f"expected {expected_bridge}"
        )

    virsh("net-start", spec["name"], check=False)
    if not exists:
        virsh("net-autostart", spec["name"])
    info = virsh("net-info", spec["name"]).stdout.lower()
    if "active:" not in info or "active:           yes" not in info:
        # Locale-independent fallback for variable spacing in virsh output.
        active = any(
            line.split(":", 1)[1].strip().lower() == "yes"
            for line in info.splitlines()
            if line.strip().startswith("active:") and ":" in line
        )
        if not active:
            raise SystemExit(f"libvirt network {spec['name']} is not active")
    print(
        f"Ready libvirt network {spec['name']} bridge={observed_bridge} "
        f"type={'management-nat' if management else 'l2-trunk'}"
    )


def parseArgs() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--ownership", type=Path, help="write UUIDs of networks defined by this invocation")
    parser.add_argument("--auto-name", help="choose a private management network for this build")
    return parser.parse_args()


def configurePrivateNetwork(config: dict[str, Any], name: str) -> None:
    """Set a free NAT subnet and generated VM IP prefix in the transient config."""
    routes = subprocess.check_output(["ip", "-j", "-4", "route", "show", "table", "all"], text=True)
    used = [
        ipaddress.ip_network(route["dst"], strict=False)
        for route in json.loads(routes) if route.get("dst") not in (None, "default")
    ]
    for network in virsh("net-list", "--all", "--name").stdout.split():
        root = ET.fromstring(virsh("net-dumpxml", network).stdout)
        for ip in root.findall("ip"):
            address = ip.get("address", "")
            if address and ":" not in address:
                mask = ip.get("prefix") or ip.get("netmask") or "32"
                used.append(ipaddress.ip_network(f"{address}/{mask}", strict=False))
    for block in ("192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8"):
        for candidate in ipaddress.ip_network(block).subnets(new_prefix=24):
            if any(candidate.overlaps(other) for other in used):
                continue
            prefix = str(candidate.network_address).rsplit(".", 1)[0]
            config["kvm"].update(
                network=name, networkBridge=f"sv{name.rsplit('-', 1)[-1]}",
                networkCidr=str(candidate), networkGateway=f"{prefix}.1",
                dhcpStart=f"{prefix}.2", dhcpEnd=f"{prefix}.254",
            )
            config.setdefault("defaults", {})["ip_prefix"] = prefix
            return
    raise SystemExit("No free private /24 was found for KVM; configure an existing kvm.network.")


def main() -> int:
    """Prepare every network needed before VM creation."""
    args = parseArgs()
    config = loadConfig(args.config)
    if args.auto_name:
        configurePrivateNetwork(config, args.auto_name)
        args.config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    created: dict[str, str] = {}
    if args.ownership is not None:
        args.ownership.write_text("{}\n", encoding="utf-8")
    ensureNetwork(managementNetworkSpec(config), management=True, created=created, ownership=args.ownership)
    for spec in extraNetworkSpecs(config):
        ensureNetwork(spec, management=False, created=created, ownership=args.ownership)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
