#!/usr/bin/env python3
"""Parse and render multi-hypervisor KVM plans for k8sTools.

The multi-host flow treats physical machines as KVM hypervisors. Each
hypervisor owns a routed libvirt subnet, while the generated VMs form one K3s
cluster. This helper converts the global kvm.yaml into host-local kvm.yaml
files and the global configK3s.yaml consumed by the K3s setup entrypoint.
"""

from __future__ import annotations

import argparse
import copy
import ipaddress
import os
import re
import shlex
from pathlib import Path
from typing import Any

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
SETUP_DIR = SCRIPT_DIR.parent
CONFIG_DIR_KEY = "__configDir"


def loadYaml(path: str | Path) -> dict[str, Any]:
    """Load one YAML mapping.

    Args:
        path: YAML file path.
    """
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid YAML root in {path}: expected a mapping")
    data[CONFIG_DIR_KEY] = str(Path(path).expanduser().resolve().parent)
    normalizeConfig(data)
    return data


def writeYaml(path: str | Path, data: dict[str, Any]) -> None:
    """Write one YAML mapping.

    Args:
        path: Output YAML path.
        data: Mapping to serialize.
    """
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def normalizeConfig(data: dict[str, Any]) -> None:
    """Normalize legacy snake_case keys while keeping YAML user-facing."""
    if "cluster_name" in data and "clusterName" not in data:
        data["clusterName"] = data.pop("cluster_name")
    for section in ("master", "workers"):
        value = data.get(section)
        if isinstance(value, dict):
            for old, new in {"memory_mb": "memoryMb", "disk_gb": "diskGb", "name_prefix": "namePrefix"}.items():
                if old in value and new not in value:
                    value[new] = value.pop(old)
    for host in data.get("hypervisors") or []:
        if not isinstance(host, dict):
            continue
        if "vm_count" in host and "vmCount" not in host:
            host["vmCount"] = host.pop("vm_count")
        if "remote_work_dir" in host and "remoteWorkDir" not in host:
            host["remoteWorkDir"] = host.pop("remote_work_dir")
        routed = host.get("routedSubnet")
        if not isinstance(routed, dict) and isinstance(host.get("routed_subnet"), dict):
            routed = host["routed_subnet"]
            host["routedSubnet"] = routed
        if isinstance(routed, dict):
            for old, new in {
                "bridge_name": "bridgeName",
                "network_name": "networkName",
                "vm_ip_start": "vmIpStart",
            }.items():
                if old in routed and new not in routed:
                    routed[new] = routed.pop(old)


def getNested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Read a nested mapping field using dotted path syntax.

    Args:
        data: Source mapping.
        path: Dotted path such as outputs.tmpDir.
        default: Value returned when the field does not exist.
    """
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        for candidate in (part, snakeCase(part), camelCase(part)):
            if candidate in cur:
                cur = cur[candidate]
                break
        else:
            return default
    return cur


def snakeCase(value: str) -> str:
    """Convert one YAML key segment to snake_case."""
    return re.sub(r"(?<!^)([A-Z])", r"_\1", value).lower()


def camelCase(value: str) -> str:
    """Convert one YAML key segment to lower camelCase."""
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def expandPath(value: str) -> str:
    """Expand local user/environment markers into an absolute path string."""
    return str(Path(os.path.expandvars(os.path.expanduser(value))).resolve())


def clusterName(data: dict[str, Any]) -> str:
    """Return the effective cluster name."""
    return str(data.get("clusterName") or "seedemu-k3s")


def outputPath(data: dict[str, Any], key: str, fallback: Path) -> str:
    """Return a local setup output path.

    Args:
        data: Parsed global kvm.yaml.
        key: outputs.* key to inspect.
        fallback: Default path when the key is absent.
    """
    configured = getNested(data, f"outputs.{key}")
    if configured:
        candidate = Path(os.path.expandvars(os.path.expanduser(str(configured))))
        if not candidate.is_absolute():
            candidate = Path(str(data.get(CONFIG_DIR_KEY) or SETUP_DIR)) / candidate
        return str(candidate.resolve())
    return str(fallback.resolve())


def hostList(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated hypervisor records.

    Args:
        data: Parsed global kvm.yaml.
    """
    raw_hosts = data.get("hypervisors")
    if not isinstance(raw_hosts, list) or not raw_hosts:
        raise SystemExit("kvm.yaml requires a non-empty hypervisors list")

    names: set[str] = set()
    networks: list[tuple[str, ipaddress.IPv4Network]] = []
    hosts: list[dict[str, Any]] = []
    for raw in raw_hosts:
        if not isinstance(raw, dict):
            raise SystemExit(f"hypervisors item must be a mapping: {raw}")
        name = str(raw.get("name") or "").strip()
        ip = str(raw.get("ip") or "").strip()
        if not name or not ip:
            raise SystemExit(f"hypervisor requires name and ip: {raw}")
        if name in names:
            raise SystemExit(f"duplicate hypervisor name: {name}")
        names.add(name)

        routed = raw.get("routedSubnet")
        if not isinstance(routed, dict):
            raise SystemExit(f"hypervisor {name} requires routedSubnet")
        cidr = str(routed.get("cidr") or "").strip()
        gateway = str(routed.get("gateway") or "").strip()
        if not cidr or not gateway:
            raise SystemExit(f"hypervisor {name} routedSubnet requires cidr and gateway")
        network = ipaddress.ip_network(cidr, strict=False)
        gateway_ip = ipaddress.ip_address(gateway)
        if gateway_ip not in network:
            raise SystemExit(f"hypervisor {name} gateway {gateway} is outside {cidr}")
        for other_name, other_network in networks:
            if network.overlaps(other_network):
                raise SystemExit(f"routedSubnet overlap: {name} {network} overlaps {other_name} {other_network}")
        networks.append((name, network))

        ssh_cfg = raw.get("ssh") if isinstance(raw.get("ssh"), dict) else {}
        hosts.append(
            {
                "name": name,
                "ip": ip,
                "connection": str(raw.get("connection") or "ssh").strip().lower(),
                "sshUser": str(ssh_cfg.get("user") or getNested(data, "hypervisorSsh.user", "")),
                "sshKey": expandPath(str(ssh_cfg.get("key") or getNested(data, "hypervisorSsh.key", "~/.ssh/id_ed25519"))),
                "vmCount": int(raw.get("vmCount") or 0),
                "networkName": str(routed.get("networkName") or f"seedemu-{name}"),
                "bridgeName": str(routed.get("bridgeName") or f"virbr-{name[:8]}"),
                "cidr": str(network),
                "gateway": str(gateway_ip),
                "netmask": str(network.netmask),
                "dhcpStart": str(firstUsableIp(network, gateway_ip)),
                "dhcpEnd": str(lastUsableIp(network, gateway_ip)),
                "vmIpStart": int(routed.get("vmIpStart") or 10),
                "remoteWorkDir": str(
                    raw.get("remoteWorkDir")
                    or getNested(data, "multiHostKvm.remoteWorkDir")
                    or f"/tmp/seedemu-k8s-tools/{clusterName(data)}/{name}"
                ),
            }
        )

    if any(host["connection"] != "local" and not host["sshUser"] for host in hosts):
        raise SystemExit("non-local hypervisors require ssh.user")
    if sum(host["vmCount"] for host in hosts) <= 0:
        raise SystemExit("at least one hypervisor vmCount must be > 0")
    return hosts


def routingTunnelConfig(data: dict[str, Any]) -> dict[str, Any]:
    """Return optional hypervisor-to-hypervisor routing tunnel settings.

    Args:
        data: Parsed global multi-host KVM YAML.

    The routed libvirt subnet model needs a valid next-hop between physical
    hypervisors. When the physical machines are only connected by routed
    underlay networks, the peer physical IP is not a valid L2 next-hop. This
    optional VXLAN tunnel creates a small point-to-point L3 next-hop per
    hypervisor pair.
    """
    raw = getNested(data, "multiHostKvm.routingTunnel")
    if not isinstance(raw, dict):
        return {"enabled": False, "type": "none"}
    tunnel_type = str(raw.get("type") or "none").strip().lower()
    enabled = bool(raw.get("enabled", tunnel_type in {"vxlan", "linux-vxlan", "linux_vxlan"}))
    if not enabled or tunnel_type in {"none", "disabled", "false"}:
        return {"enabled": False, "type": "none"}
    if tunnel_type not in {"vxlan", "linux-vxlan", "linux_vxlan"}:
        raise SystemExit(f"unsupported multiHostKvm.routingTunnel.type: {tunnel_type}")
    cidr = str(raw.get("cidr") or "10.255.80.0/24")
    network = ipaddress.ip_network(cidr, strict=False)
    if network.version != 4 or network.num_addresses < 4:
        raise SystemExit(f"routingTunnel.cidr must be an IPv4 network with at least four addresses: {cidr}")
    return {
        "enabled": True,
        "type": "vxlan",
        "cidr": str(network),
        "namePrefix": str(raw.get("namePrefix") or "vxkvm"),
        "vniBase": int(raw.get("vniBase") or 4280),
        "dstPort": int(raw.get("dstPort") or 4790),
    }


def tunnelRows(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one VXLAN tunnel route row per ordered hypervisor pair.

    Args:
        data: Parsed global multi-host KVM YAML.
    """
    config = routingTunnelConfig(data)
    if not config["enabled"]:
        return []
    hosts = hostList(data)
    rows: list[dict[str, Any]] = []
    network = ipaddress.ip_network(str(config["cidr"]), strict=False)
    pair_index = 0
    for left_index, left in enumerate(hosts):
        for right in hosts[left_index + 1 :]:
            base_ip = int(network.network_address) + 4 * pair_index
            local_a = ipaddress.ip_address(base_ip + 1)
            local_b = ipaddress.ip_address(base_ip + 2)
            if local_b >= network.broadcast_address:
                raise SystemExit(f"routingTunnel.cidr {network} is too small for all hypervisor pairs")
            iface = f"{config['namePrefix']}{pair_index}"
            if len(iface) > 15:
                raise SystemExit(f"routing tunnel interface name too long: {iface}")
            vni = int(config["vniBase"]) + pair_index
            common = {"interface": iface, "vni": vni, "dstPort": int(config["dstPort"])}
            rows.append(
                {
                    **common,
                    "host": left["name"],
                    "peerName": right["name"],
                    "localPhysicalIp": left["ip"],
                    "peerPhysicalIp": right["ip"],
                    "localTunnelCidr": f"{local_a}/30",
                    "peerTunnelIp": str(local_b),
                    "remoteCidr": right["cidr"],
                }
            )
            rows.append(
                {
                    **common,
                    "host": right["name"],
                    "peerName": left["name"],
                    "localPhysicalIp": right["ip"],
                    "peerPhysicalIp": left["ip"],
                    "localTunnelCidr": f"{local_b}/30",
                    "peerTunnelIp": str(local_a),
                    "remoteCidr": left["cidr"],
                }
            )
            pair_index += 1
    return rows


def firstUsableIp(network: ipaddress.IPv4Network, gateway: ipaddress.IPv4Address) -> ipaddress.IPv4Address:
    """Return the first usable DHCP range IP for a routed subnet."""
    for candidate in network.hosts():
        if candidate != gateway:
            return candidate
    raise SystemExit(f"network {network} has no usable host IP")


def lastUsableIp(network: ipaddress.IPv4Network, gateway: ipaddress.IPv4Address) -> ipaddress.IPv4Address:
    """Return the last usable DHCP range IP for a routed subnet."""
    last = None
    for candidate in network.hosts():
        if candidate != gateway:
            last = candidate
    if last is None:
        raise SystemExit(f"network {network} has no usable host IP")
    return last


def requireHost(hosts: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Return a hypervisor by name."""
    for host in hosts:
        if host["name"] == name:
            return host
    raise SystemExit(f"unknown hypervisor: {name}")


def allocateHostIps(host: dict[str, Any], count: int) -> list[str]:
    """Allocate VM IP addresses inside one hypervisor subnet."""
    network = ipaddress.ip_network(host["cidr"], strict=False)
    gateway = ipaddress.ip_address(host["gateway"])
    current = int(network.network_address) + int(host["vmIpStart"])
    end = int(network.broadcast_address) - 1
    result: list[str] = []
    while current <= end and len(result) < count:
        candidate = ipaddress.ip_address(current)
        current += 1
        if candidate != gateway and candidate in network:
            result.append(str(candidate))
    if len(result) != count:
        raise SystemExit(f"not enough VM IPs in {host['cidr']} for host {host['name']}")
    return result


def allocateMac(index: int, data: dict[str, Any]) -> str:
    """Allocate one deterministic MAC address for the global VM plan."""
    prefix = str(getNested(data, "multiHostKvm.macPrefix", "52:54:00:65:10")).lower()
    start = int(getNested(data, "multiHostKvm.macStart", 0x10))
    if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){4}", prefix):
        raise SystemExit(f"multiHostKvm.macPrefix must contain five MAC octets: {prefix}")
    suffix = start + index
    if suffix > 255:
        raise SystemExit("multiHostKvm MAC allocation exhausted one-byte suffix space")
    return f"{prefix}:{suffix:02x}"


def vmPlan(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the full VM plan across all hypervisors."""
    hosts = hostList(data)
    master_cfg = data.get("master") if isinstance(data.get("master"), dict) else {}
    workers_cfg = data.get("workers") if isinstance(data.get("workers"), dict) else {}
    master_host_name = str(master_cfg.get("placement") or hosts[0]["name"])
    requireHost(hosts, master_host_name)
    master_name = str(master_cfg.get("name") or "seed-k3s-master")
    worker_prefix = str(workers_cfg.get("namePrefix") or "seed-k3s-worker")
    master_resources = {
        "vcpus": int(master_cfg.get("vcpus") or 16),
        "memory_mb": int(master_cfg.get("memoryMb") or 32768),
        "disk_gb": int(master_cfg.get("diskGb") or 120),
    }
    worker_resources = {
        "vcpus": int(workers_cfg.get("vcpus") or 8),
        "memory_mb": int(workers_cfg.get("memoryMb") or 16384),
        "disk_gb": int(workers_cfg.get("diskGb") or 80),
    }

    nodes: list[dict[str, Any]] = []
    worker_number = 1
    master_created = False
    global_index = 0
    for host in hosts:
        for host_index, vm_ip in enumerate(allocateHostIps(host, host["vmCount"]), start=1):
            if host["name"] == master_host_name and not master_created:
                role = "master"
                name = master_name
                resources = master_resources
                master_created = True
            else:
                role = "worker"
                name = f"{worker_prefix}{worker_number}"
                resources = worker_resources
                worker_number += 1
            nodes.append(
                {
                    "name": name,
                    "role": role,
                    "ip": vm_ip,
                    "mac": allocateMac(global_index, data),
                    "vcpus": resources["vcpus"],
                    "memory_mb": resources["memory_mb"],
                    "disk_gb": resources["disk_gb"],
                    "hypervisor": host["name"],
                    "hypervisorIp": host["ip"],
                    "hostIndex": host_index,
                }
            )
            global_index += 1
    if not master_created:
        raise SystemExit(f"master placement host {master_host_name} has vmCount=0")
    validateVmPlan(nodes)
    return nodes


def validateVmPlan(nodes: list[dict[str, Any]]) -> None:
    """Validate generated VM names, IPs, MACs and master cardinality."""
    masters = [node for node in nodes if node["role"] == "master"]
    if len(masters) != 1:
        raise SystemExit(f"expected exactly one master VM, got {len(masters)}")
    for key in ("name", "ip", "mac"):
        values = [str(node[key]) for node in nodes]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise SystemExit(f"duplicate VM {key}: {duplicates}")


def passThroughSections(data: dict[str, Any]) -> dict[str, Any]:
    """Return K3s-stage sections copied into global configK3s.yaml."""
    payload: dict[str, Any] = {}
    for section in ("registry", "k3s", "fabric", "ovn", "cni", "tuning", "seedemu"):
        value = data.get(section)
        if isinstance(value, dict) and value:
            payload[section] = copy.deepcopy(value)
    if str(getNested(payload, "fabric.type", "")).lower() in {"ovn", "kube-ovn", "kube_ovn"}:
        k3s = payload.setdefault("k3s", {})
        if isinstance(k3s, dict):
            k3s.setdefault("version", "v1.29.15+k3s1")
    cluster = clusterName(data)
    payload["outputs"] = {
        "tmpDir": outputPath(data, "tmpDir", SETUP_DIR / "tmp"),
        "kubeconfig": outputPath(data, "kubeconfig", SETUP_DIR / f"{cluster}.kubeconfig.yaml"),
        "inventory": outputPath(data, "inventory", SETUP_DIR / f"{cluster}.inventory.yaml"),
    }
    return payload


def hostNodes(data: dict[str, Any], host_name: str) -> list[dict[str, Any]]:
    """Return planned VMs assigned to one hypervisor."""
    return [node for node in vmPlan(data) if node["hypervisor"] == host_name]


def printShellVars(args: argparse.Namespace) -> None:
    """Print global setup output paths as shell assignments."""
    data = loadYaml(args.config)
    values = {
        "outputConfigK3s": outputPath(data, "k3sConfig", SETUP_DIR / "configK3s.yaml"),
        "outputMultiHostKvmState": outputPath(data, "multiHostKvmState", SETUP_DIR / "multiHostKvmState.yaml"),
        "outputTmpDir": outputPath(data, "tmpDir", SETUP_DIR / "tmp"),
    }
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def printHostsTsv(args: argparse.Namespace) -> None:
    """Print hypervisor records consumed by shell scripts."""
    for host in hostList(loadYaml(args.config)):
        print(
            "\t".join(
                str(host[key])
                for key in (
                    "name",
                    "ip",
                    "connection",
                    "sshUser",
                    "sshKey",
                    "networkName",
                    "bridgeName",
                    "cidr",
                    "gateway",
                    "remoteWorkDir",
                )
            )
        )


def printHostRoutesTsv(args: argparse.Namespace) -> None:
    """Print static routes needed by one hypervisor."""
    data = loadYaml(args.config)
    tunnel_by_peer = {row["peerName"]: row for row in tunnelRows(data) if row["host"] == args.host}
    for host in hostList(data):
        if host["name"] == args.host:
            continue
        tunnel = tunnel_by_peer.get(host["name"])
        if tunnel:
            print("\t".join([host["cidr"], tunnel["peerTunnelIp"], host["name"], tunnel["interface"]]))
        else:
            print("\t".join([host["cidr"], host["ip"], host["name"], ""]))


def printHostTunnelsTsv(args: argparse.Namespace) -> None:
    """Print VXLAN tunnel rows needed by one hypervisor."""
    for row in tunnelRows(loadYaml(args.config)):
        if row["host"] != args.host:
            continue
        print(
            "\t".join(
                str(row[key])
                for key in (
                    "interface",
                    "vni",
                    "dstPort",
                    "localPhysicalIp",
                    "peerPhysicalIp",
                    "localTunnelCidr",
                    "peerTunnelIp",
                    "peerName",
                )
            )
        )


def hostVmSshKeyPaths(data: dict[str, Any], host_name: str) -> tuple[str, str]:
    """Return local source key and hypervisor-local target key paths.

    Args:
        data: Parsed global multi-host KVM YAML.
        host_name: Hypervisor name.

    The global configK3s.yaml keeps the user's local VM SSH key path so the
    control host can install K3s. Remote hypervisors also need a local copy of
    the same key while creating VMs and waiting for cloud-init SSH readiness.
    """
    host = requireHost(hostList(data), host_name)
    vm_ssh = data.get("vmSsh") if isinstance(data.get("vmSsh"), dict) else {}
    source_key = expandPath(str(vm_ssh.get("key") or "~/.ssh/id_ed25519"))
    if host["connection"] == "local":
        return source_key, source_key
    target_key = str(
        vm_ssh.get("remoteHypervisorKey")
        or vm_ssh.get("remoteKey")
        or f"{host['remoteWorkDir']}/ssh/{Path(source_key).name}"
    )
    return source_key, target_key


def printHostVmSshKeyTsv(args: argparse.Namespace) -> None:
    """Print VM SSH key source/target paths for one hypervisor."""
    source_key, target_key = hostVmSshKeyPaths(loadYaml(args.config), args.host)
    source_pub = f"{source_key}.pub"
    target_pub = f"{target_key}.pub"
    print("\t".join([source_key, target_key, source_pub, target_pub]))


def writeHostNetworkXml(args: argparse.Namespace) -> None:
    """Write libvirt routed network XML for one hypervisor."""
    host = requireHost(hostList(loadYaml(args.config)), args.host)
    xml = f"""<network>
  <name>{host['networkName']}</name>
  <forward mode='route'/>
  <bridge name='{host['bridgeName']}' stp='on' delay='0'/>
  <ip address='{host['gateway']}' netmask='{host['netmask']}'>
    <dhcp>
      <range start='{host['dhcpStart']}' end='{host['dhcpEnd']}'/>
    </dhcp>
  </ip>
</network>
"""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(xml, encoding="utf-8")
    print(output)


def writeHostLocalKvm(args: argparse.Namespace) -> None:
    """Write host-local kvm.yaml consumed by kvm/createKvmVms.py."""
    data = loadYaml(args.config)
    host = requireHost(hostList(data), args.host)
    vm_ssh = data.get("vmSsh") if isinstance(data.get("vmSsh"), dict) else {}
    ssh_user = str(vm_ssh.get("user") or "ubuntu")
    _, ssh_key = hostVmSshKeyPaths(data, args.host)
    seedemu = data.get("seedemu") if isinstance(data.get("seedemu"), dict) else {}
    host_work_dir = str(host["remoteWorkDir"])
    payload = {
        "clusterName": clusterName(data),
        "nodes": [
            {
                "name": node["name"],
                "role": node["role"],
                "ip": node["ip"],
                "mac": node["mac"],
                "vcpus": node["vcpus"],
                "memory_mb": node["memory_mb"],
                "disk_gb": node["disk_gb"],
            }
            for node in hostNodes(data, args.host)
        ],
        "ssh": {"user": ssh_user, "key": ssh_key},
        "kvm": {
            "network": host["networkName"],
            "storageDir": host_work_dir,
            "diskDir": f"{host_work_dir}/disks",
            "cloudInitDir": f"{host_work_dir}/cloud-init",
            "baseImagePath": f"{host_work_dir}/base/jammy-server-cloudimg-amd64.img",
            "skipK3sConfig": True,
        },
        "outputs": {
            "tmpDir": f"{host_work_dir}/tmp",
            "kvmState": f"{host_work_dir}/kvmState.yaml",
        },
    }
    if seedemu:
        payload["seedemu"] = copy.deepcopy(seedemu)
    writeYaml(args.output, payload)
    print(args.output)


def writeGlobalK3sConfig(args: argparse.Namespace) -> None:
    """Write global configK3s.yaml for the VM cluster."""
    data = loadYaml(args.config)
    vm_ssh = data.get("vmSsh") if isinstance(data.get("vmSsh"), dict) else {}
    ssh_user = str(vm_ssh.get("user") or "ubuntu")
    ssh_key = expandPath(str(vm_ssh.get("key") or "~/.ssh/id_ed25519"))
    payload: dict[str, Any] = {
        "clusterName": clusterName(data),
        "nodes": [
            {
                "name": node["name"],
                "role": node["role"],
                "ip": node["ip"],
                "vcpus": int(node.get("vcpus") or 0),
                "memoryMb": int(node.get("memoryMb") or node.get("memory_mb") or 0),
                "diskGb": int(node.get("diskGb") or node.get("disk_gb") or 0),
                "ssh": {"user": ssh_user, "key": ssh_key},
            }
            for node in vmPlan(data)
        ],
    }
    payload.update(passThroughSections(data))
    writeYaml(args.output, payload)
    print(args.output)


def writeState(args: argparse.Namespace) -> None:
    """Write multiHostKvmState.yaml for cleanup and auditing."""
    data = loadYaml(args.config)
    payload = {
        "clusterName": clusterName(data),
        "hypervisors": hostList(data),
        "nodes": vmPlan(data),
        "routingTunnel": routingTunnelConfig(data),
        "tunnelRows": tunnelRows(data),
        "outputs": {
            "configK3s": outputPath(data, "k3sConfig", SETUP_DIR / "configK3s.yaml"),
            "kubeconfig": outputPath(data, "kubeconfig", SETUP_DIR / f"{clusterName(data)}.kubeconfig.yaml"),
            "inventory": outputPath(data, "inventory", SETUP_DIR / f"{clusterName(data)}.inventory.yaml"),
        },
    }
    writeYaml(args.output, payload)
    print(args.output)


def loadState(path: str | Path) -> dict[str, Any]:
    """Load and validate multiHostKvmState.yaml."""
    data = loadYaml(path)
    if not isinstance(data.get("hypervisors"), list):
        raise SystemExit(f"Invalid multiHostKvmState.yaml: missing hypervisors list in {path}")
    return data


def printStateHostsTsv(args: argparse.Namespace) -> None:
    """Print hypervisor records from multiHostKvmState.yaml."""
    data = loadState(args.state)
    for host in data["hypervisors"]:
        print(
            "\t".join(
                str(host.get(key) or "")
                for key in (
                    "name",
                    "ip",
                    "connection",
                    "sshUser",
                    "sshKey",
                    "networkName",
                    "bridgeName",
                    "cidr",
                    "gateway",
                    "remoteWorkDir",
                )
            )
        )


def printStateRoutesTsv(args: argparse.Namespace) -> None:
    """Print cleanup routes from multiHostKvmState.yaml."""
    data = loadState(args.state)
    current_names = {str(host.get("name")) for host in data["hypervisors"]}
    if args.host not in current_names:
        raise SystemExit(f"unknown hypervisor in state: {args.host}")
    tunnel_rows = data.get("tunnelRows") if isinstance(data.get("tunnelRows"), list) else []
    if tunnel_rows:
        for row in tunnel_rows:
            if row.get("host") == args.host:
                print(
                    "\t".join(
                        [
                            str(row.get("remoteCidr") or ""),
                            str(row.get("peerTunnelIp") or ""),
                            str(row.get("peerName") or ""),
                            str(row.get("interface") or ""),
                        ]
                    )
                )
        return
    for host in data["hypervisors"]:
        if host.get("name") == args.host:
            continue
        print("\t".join([str(host.get("cidr") or ""), str(host.get("ip") or ""), str(host.get("name") or ""), ""]))


def printStateTunnelsTsv(args: argparse.Namespace) -> None:
    """Print VXLAN tunnel rows from multiHostKvmState.yaml for cleanup."""
    data = loadState(args.state)
    tunnel_rows = data.get("tunnelRows") if isinstance(data.get("tunnelRows"), list) else []
    for row in tunnel_rows:
        if row.get("host") != args.host:
            continue
        print(
            "\t".join(
                str(row.get(key) or "")
                for key in (
                    "interface",
                    "vni",
                    "dstPort",
                    "localPhysicalIp",
                    "peerPhysicalIp",
                    "localTunnelCidr",
                    "peerTunnelIp",
                    "peerName",
                )
            )
        )


def printStateOutputVars(args: argparse.Namespace) -> None:
    """Print generated output paths from multiHostKvmState.yaml."""
    data = loadState(args.state)
    outputs = data.get("outputs") if isinstance(data.get("outputs"), dict) else {}
    values = {
        "stateConfigK3s": outputs.get("configK3s") or str(SETUP_DIR / "configK3s.yaml"),
        "stateKubeconfig": outputs.get("kubeconfig") or str(SETUP_DIR / f"{data.get('clusterName', 'seedemu-k3s')}.kubeconfig.yaml"),
        "stateInventory": outputs.get("inventory") or str(SETUP_DIR / f"{data.get('clusterName', 'seedemu-k3s')}.inventory.yaml"),
    }
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def validate(args: argparse.Namespace) -> None:
    """Validate a global multi-host KVM config."""
    data = loadYaml(args.config)
    hosts = hostList(data)
    nodes = vmPlan(data)
    print(f"Validated {len(hosts)} hypervisors and {len(nodes)} VMs.")


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate").set_defaults(func=validate)
    sub.add_parser("shell-vars").set_defaults(func=printShellVars)
    sub.add_parser("hosts-tsv").set_defaults(func=printHostsTsv)

    routes = sub.add_parser("host-routes-tsv")
    routes.add_argument("--host", required=True)
    routes.set_defaults(func=printHostRoutesTsv)

    tunnels = sub.add_parser("host-tunnels-tsv")
    tunnels.add_argument("--host", required=True)
    tunnels.set_defaults(func=printHostTunnelsTsv)

    vm_key = sub.add_parser("host-vm-ssh-key-tsv")
    vm_key.add_argument("--host", required=True)
    vm_key.set_defaults(func=printHostVmSshKeyTsv)

    network_xml = sub.add_parser("write-host-network-xml")
    network_xml.add_argument("--host", required=True)
    network_xml.add_argument("--output", required=True)
    network_xml.set_defaults(func=writeHostNetworkXml)

    local_kvm = sub.add_parser("write-host-local-kvm")
    local_kvm.add_argument("--host", required=True)
    local_kvm.add_argument("--output", required=True)
    local_kvm.set_defaults(func=writeHostLocalKvm)

    global_config = sub.add_parser("write-global-k3s-config")
    global_config.add_argument("--output", required=True)
    global_config.set_defaults(func=writeGlobalK3sConfig)

    state = sub.add_parser("write-state")
    state.add_argument("--output", required=True)
    state.set_defaults(func=writeState)

    state_hosts = sub.add_parser("state-hosts-tsv")
    state_hosts.add_argument("--state", required=True)
    state_hosts.set_defaults(func=printStateHostsTsv)

    state_routes = sub.add_parser("state-routes-tsv")
    state_routes.add_argument("--state", required=True)
    state_routes.add_argument("--host", required=True)
    state_routes.set_defaults(func=printStateRoutesTsv)

    state_tunnels = sub.add_parser("state-tunnels-tsv")
    state_tunnels.add_argument("--state", required=True)
    state_tunnels.add_argument("--host", required=True)
    state_tunnels.set_defaults(func=printStateTunnelsTsv)

    state_outputs = sub.add_parser("state-output-vars")
    state_outputs.add_argument("--state", required=True)
    state_outputs.set_defaults(func=printStateOutputVars)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
