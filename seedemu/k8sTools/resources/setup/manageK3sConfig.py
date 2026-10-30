#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import yaml


SETUP_DIR = Path(__file__).resolve().parent
_LOCAL_IPS: set[str] | None = None


def expandPath(value: str) -> str:
    """Expand ~ and return an absolute path string."""
    return str(Path(os.path.expanduser(value)).resolve())


def readLocalIps() -> set[str]:
    """Return IP addresses configured on the host running this helper.

    The K3s setup scripts use this to detect the common physical-server case
    where the configured master node is the current machine and should be
    handled with local commands instead of SSH-to-self.
    """
    global _LOCAL_IPS
    if _LOCAL_IPS is not None:
        return _LOCAL_IPS
    ips = {"127.0.0.1", "::1", "localhost"}
    try:
        output = subprocess.check_output(
            ["ip", "-o", "addr", "show"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in output.splitlines():
            parts = line.split()
            for token in parts:
                if "/" not in token:
                    continue
                address = token.split("/", 1)[0]
                if address and (address[0].isdigit() or ":" in address):
                    ips.add(address)
    except Exception:
        pass
    _LOCAL_IPS = ips
    return ips


def defaultSeedEmulatorDockerDir() -> str:
    """Return the best-known host path for SeedEMU base/router Dockerfiles."""
    candidates = []
    for base in (SETUP_DIR, *SETUP_DIR.parents):
        candidates.append(base / "docker_images/multiarch")
    candidates.extend(
        [
            Path.home() / "seed-emulator/docker_images/multiarch",
            Path.home() / "seed-emulator-k8s-new/docker_images/multiarch",
            Path.home() / "k8s/seed-emulator/docker_images/multiarch",
        ]
    )
    for candidate in candidates:
        if (candidate / "seedemu-base").is_dir() and (candidate / "seedemu-router").is_dir():
            return str(candidate.resolve())
    return str(candidates[0].expanduser().resolve())


def getNested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Read a dotted YAML path, accepting both camelCase and snake_case keys."""
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        candidates = [part, _snakeCase(part), _camelCase(part)]
        found = False
        for candidate in candidates:
            if candidate in cur:
                cur = cur[candidate]
                found = True
                break
        if not found:
            return default
    return cur


def loadYaml(path: str) -> dict[str, Any]:
    """Load configK3s.yaml and validate that it is a mapping."""
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid YAML root in {path}: expected mapping")
    return data


def normalizeRole(name: str, role: str | None, index: int) -> str:
    """Normalize user node roles; role must be explicitly provided."""
    if not role:
        raise SystemExit(f"Node {name or index} requires role: master or worker")
    if role in {"master", "control-plane", "server"}:
        return "master"
    if role in {"worker", "agent"}:
        return "worker"
    raise SystemExit(f"Unsupported role for node {name or index}: {role}")


def yamlNodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized nodes from configK3s.yaml.

    Each node requires an IP address and should carry its own ssh.user/key.
    Missing names become seed-k3s-master/seed-k3s-workerN. A top-level ssh
    block is still accepted as a compatibility fallback, but generated configs
    write SSH settings per node.
    """
    raw_nodes = data.get("nodes") or []
    if not isinstance(raw_nodes, list):
        raise SystemExit("configK3s.yaml field nodes must be a list")
    out: list[dict[str, Any]] = []
    for index, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid node item: {item}")
        ip = str(item.get("ip") or item.get("managementIp") or item.get("management_ip") or "")
        if not ip:
            raise SystemExit(f"Each k3s node requires an ip: {item}")
        role = normalizeRole(str(item.get("name") or ""), str(item.get("role") or ""), index)
        default_name = "seed-k3s-master" if role == "master" else f"seed-k3s-worker{sum(1 for node in out if node['role'] == 'worker') + 1}"
        name = str(item.get("name") or default_name)
        ssh_user, ssh_key = nodeSshSettings(data, item, name)
        connection = nodeConnection(item, ip, ssh_user)
        out.append(
            {
                "name": name,
                "role": role,
                "ip": ip,
                "mac": str(item.get("mac") or ""),
                "vcpus": int(item.get("vcpus") or 0),
                "memoryMb": int(item.get("memoryMb") or item.get("memory_mb") or 0),
                "diskGb": int(item.get("diskGb") or item.get("disk_gb") or 0),
                "sshUser": ssh_user,
                "sshKey": expandPath(ssh_key),
                "connection": connection,
            }
        )
    validateNodes(out)
    return out


def nodeSshSettings(data: dict[str, Any], item: dict[str, Any], node_name: str) -> tuple[str, str]:
    """Return SSH user/key for one node.

    Args:
        data: Full configK3s.yaml mapping.
        item: One raw node mapping.
        node_name: Normalized node name used for error messages.
    """
    ssh = item.get("ssh") if isinstance(item.get("ssh"), dict) else {}
    user = ssh.get("user") or getNested(data, "ssh.user")
    key = ssh.get("key") or getNested(data, "ssh.key")
    if not user or not key:
        raise SystemExit(
            f"Node {node_name} requires ssh.user and ssh.key. "
            "Use nodes[].ssh.{user,key}; top-level ssh is accepted only as a fallback."
        )
    return str(user), str(key)


def nodeConnection(item: dict[str, Any], ip: str, ssh_user: str) -> str:
    """Return how setup scripts should reach one node.

    Args:
        item: Raw node mapping from configK3s.yaml.
        ip: Normalized management IP.
        ssh_user: Normalized SSH user.

    YAML may explicitly set nodes[].connection to "local" or "ssh". If it is
    omitted, this helper treats a node as local only when its IP is assigned to
    the current host and the SSH user equals the current local user.
    """
    raw = item.get("connection") or item.get("connect")
    if raw:
        normalized = str(raw).strip().lower()
        if normalized in {"local", "localhost"}:
            return "local"
        if normalized in {"ssh", "remote"}:
            return "ssh"
        raise SystemExit(f"Unsupported node connection for {ip}: {raw}")
    if item.get("local") is True:
        return "local"
    if ip in readLocalIps() and ssh_user == getpass.getuser():
        return "local"
    return "ssh"


def validateNodes(nodes: list[dict[str, Any]]) -> None:
    """Validate that the selected node set can form one K3s cluster."""
    if not nodes:
        raise SystemExit("No nodes selected for K3s cluster")
    masters = [node for node in nodes if node["role"] == "master"]
    if len(masters) != 1:
        names = ", ".join(node["name"] for node in masters) or "none"
        raise SystemExit(f"Expected exactly one master node, got {len(masters)}: {names}")
    seen_names: set[str] = set()
    seen_ips: set[str] = set()
    for node in nodes:
        if node["name"] in seen_names:
            raise SystemExit(f"Duplicate node name: {node['name']}")
        if node["ip"] in seen_ips:
            raise SystemExit(f"Duplicate node ip: {node['ip']}")
        seen_names.add(node["name"])
        seen_ips.add(node["ip"])


def installVersion(data: dict[str, Any]) -> str:
    """Return the K3s install version expected by the configured artifact URL."""
    version = str(getNested(data, "k3s.version", "v1.28.5+k3s1"))
    artifact = str(getNested(data, "k3s.artifactUrl", "https://rancher-mirror.rancher.cn/k3s"))
    configured = getNested(data, "k3s.installVersion")
    if configured:
        return str(configured)
    if "rancher-mirror.rancher.cn/k3s" in artifact:
        return version.replace("+", "-")
    return version


def masterNode(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the unique master node."""
    return [node for node in nodes if node["role"] == "master"][0]


def configValues(data: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the local shell variable values consumed by applyK3sCluster.py."""
    cluster_name = str(data.get("clusterName") or data.get("cluster_name") or "seedemu-k3s")
    master = masterNode(nodes)
    registry_host = getNested(data, "registry.host", master["ip"])
    fabric_type = str(getNested(data, "fabric.type", "none"))
    default_cni_master = getNested(data, "fabric.bridgeName", "br-seedemu") if fabric_type == "linux-vxlan" else "ens2"
    return {
        "clusterName": cluster_name,
        "setupTmpDir": expandPath(str(getNested(data, "outputs.tmpDir", SETUP_DIR / "tmp"))),
        "k3sUser": master["sshUser"],
        "k3sSshKey": master["sshKey"],
        "k3sMasterName": master["name"],
        "k3sMasterIp": master["ip"],
        "k3sMasterConnection": master["connection"],
        "k3sVersion": getNested(data, "k3s.version", "v1.28.5+k3s1"),
        "k3sInstallVersion": installVersion(data),
        "k3sArtifactUrl": getNested(data, "k3s.artifactUrl", "https://rancher-mirror.rancher.cn/k3s"),
        "k3sForceReinstall": str(getNested(data, "k3s.forceReinstall", True)).lower(),
        "k3sClusterCidr": getNested(data, "k3s.clusterCidr", "10.42.0.0/16"),
        "k3sServiceCidr": getNested(data, "k3s.serviceCidr", "10.43.0.0/16"),
        "k3sFlannelBackend": getNested(data, "k3s.flannelBackend", "host-gw"),
        "k3sNodeCidrMaskSizeIpv4": getNested(data, "k3s.nodeCidrMaskSizeIpv4", 20),
        "k3sMaxPods": getNested(data, "k3s.maxPods", 4000),
        "kubeletRegistryQps": getNested(data, "k3s.kubeletRegistryQps", 100),
        "kubeletRegistryBurst": getNested(data, "k3s.kubeletRegistryBurst", 20),
        "registryHost": registry_host,
        "registryPort": getNested(data, "registry.port", 5000),
        "fabricType": fabric_type,
        "dockerIoMirrorEndpoint": getNested(data, "registry.dockerIoMirrorEndpoint", "https://docker.m.daocloud.io"),
        "seedEmulatorDockerDir": expandPath(str(getNested(data, "seedemu.dockerImagesDir", defaultSeedEmulatorDockerDir()))),
        "cniMasterInterface": getNested(data, "cni.defaultMasterInterface", default_cni_master),
        "cni0HashMax": getNested(data, "tuning.cni0HashMax", 16384),
        "userMaxNetNamespaces": getNested(data, "tuning.userMaxNetNamespaces", 65536),
        "neighGcThresh1": getNested(data, "tuning.neighGcThresh1", 1048576),
        "neighGcThresh2": getNested(data, "tuning.neighGcThresh2", 4194304),
        "neighGcThresh3": getNested(data, "tuning.neighGcThresh3", 8388608),
        "netdevMaxBacklog": getNested(data, "tuning.netdevMaxBacklog", 1000000),
        "optmemMax": getNested(data, "tuning.optmemMax", 25165824),
        "rebootAfterTuning": str(getNested(data, "tuning.rebootAfterTuning", False)).lower(),
        "outputKubeconfig": expandPath(str(getNested(data, "outputs.kubeconfig", SETUP_DIR / f"{cluster_name}.kubeconfig.yaml"))),
        "outputInventory": expandPath(str(getNested(data, "outputs.inventory", SETUP_DIR / f"{cluster_name}.inventory.yaml"))),
    }


def fabricValues(data: dict[str, Any]) -> dict[str, Any]:
    """Return normalized Linux fabric settings from configK3s.yaml.

    Args:
        data: Parsed configK3s.yaml mapping.

    The first implementation intentionally supports a two-node Linux VXLAN
    fabric. Larger physical fabrics should use a real L2/VLAN/EVPN/OVS design
    instead of an implicit command-driven full mesh.
    """
    values = {
        "fabricType": str(getNested(data, "fabric.type", "none")),
        "fabricBridgeName": str(getNested(data, "fabric.bridgeName", "br-seedemu")),
        "fabricVxlanName": str(getNested(data, "fabric.vxlanName", "vxseed0")),
        "fabricMacvlanTestName": str(getNested(data, "fabric.macvlanTestName", "macseed0")),
        "fabricVni": int(getNested(data, "fabric.vni", 4242)),
        "fabricDstPort": int(getNested(data, "fabric.dstPort", 4789)),
        "fabricMtu": int(getNested(data, "fabric.mtu", 1450)),
    }
    validateInterfaceName(values["fabricBridgeName"], "fabric.bridgeName")
    validateInterfaceName(values["fabricVxlanName"], "fabric.vxlanName")
    validateInterfaceName(values["fabricMacvlanTestName"], "fabric.macvlanTestName")
    return values


def ovnValues(data: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Return Kube-OVN non-primary CNI settings from configK3s.yaml.

    Args:
        data: Parsed configK3s.yaml mapping.
        nodes: Normalized node list used to discover the master IP.

    These values are consumed by ovn/installKubeOvnFabric.py. Kube-OVN runs as
    a secondary CNI while K3s/flannel remains the primary eth0 network.
    """
    vals = configValues(data, nodes)
    return {
        "ovnChartVersion": str(getNested(data, "ovn.chartVersion", "v1.15.12")),
        "ovnHelmRepoName": str(getNested(data, "ovn.helmRepoName", "kubeovn")),
        "ovnHelmRepoUrl": str(getNested(data, "ovn.helmRepoUrl", "https://kubeovn.github.io/kube-ovn/")),
        "ovnReleaseName": str(getNested(data, "ovn.releaseName", "kube-ovn")),
        "ovnNamespace": str(getNested(data, "ovn.namespace", "kube-system")),
        "ovnTunnelType": str(getNested(data, "ovn.tunnelType", "geneve")),
        "ovnIface": str(getNested(data, "ovn.iface", "")),
        "ovnPodCidr": str(getNested(data, "ovn.podCidr", "172.28.0.0/16")),
        "ovnPodGateway": str(getNested(data, "ovn.podGateway", "172.28.0.1")),
        "ovnJoinCidr": str(getNested(data, "ovn.joinCidr", "100.64.0.0/16")),
        "ovnServiceCidr": str(getNested(data, "ovn.serviceCidr", vals["k3sServiceCidr"])),
        "ovnCniConfDir": str(getNested(data, "ovn.cniConfDir", "/var/lib/rancher/k3s/agent/etc/cni/net.d")),
        "ovnMountCniConfDir": str(getNested(data, "ovn.mountCniConfDir", "/var/lib/rancher/k3s/agent/etc/cni/net.d")),
        "ovnCniBinDir": str(getNested(data, "ovn.cniBinDir", "/var/lib/rancher/k3s/data/cni")),
        "ovnHelmCacheDir": expandPath(str(getNested(data, "ovn.helmCacheDir", Path(vals["setupTmpDir"]) / "helm"))),
        "ovnMasterNodes": str(getNested(data, "ovn.masterNodes", vals["k3sMasterIp"])),
    }


def validateInterfaceName(name: str, field: str) -> None:
    """Validate Linux interface-name length before ip-link commands run."""
    if not name:
        raise SystemExit(f"{field} must not be empty")
    if len(name) > 15:
        raise SystemExit(f"{field}={name!r} is too long for Linux IFNAMSIZ; use at most 15 characters")


def sshOptions(key_path: str) -> list[str]:
    """Return SSH options used for non-interactive node inspection.

    Args:
        key_path: Private key path from nodes[].ssh.key.
    """
    return [
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "ConnectTimeout=10",
        "-i",
        key_path,
    ]


def parseRouteInterface(output: str, node_name: str, peer_ip: str) -> str:
    """Extract the outbound Linux interface from `ip -o route get` output.

    Args:
        output: Text returned by `ip -o route get <peerIp>`.
        node_name: Node name used for error messages.
        peer_ip: Peer management IP used for error messages.
    """
    match = re.search(r"(?:^|\s)dev\s+(\S+)", output)
    if not match:
        raise SystemExit(
            f"Could not detect underlay interface for {node_name}; "
            f"`ip -o route get {peer_ip}` returned: {output.strip()!r}. "
            "Set fabric.nodes.<node>.underlayInterface explicitly."
        )
    return match.group(1)


def detectUnderlayInterface(node: dict[str, Any], peer_ip: str) -> str:
    """Detect the interface a node uses to reach its VXLAN peer.

    Args:
        node: Normalized node mapping from yamlNodes().
        peer_ip: Management IP of the opposite VXLAN endpoint.

    For local nodes this runs `ip -o route get` directly. For remote nodes it
    runs the same command through SSH using nodes[].ssh.{user,key}. This keeps
    user YAML minimal while still allowing explicit underlayInterface override.
    """
    command = f"ip -o route get {shlex.quote(peer_ip)}"
    try:
        if node["connection"] == "local":
            output = subprocess.check_output(
                ["bash", "-lc", command],
                stdin=subprocess.DEVNULL,
                text=True,
                stderr=subprocess.STDOUT,
            )
        else:
            output = subprocess.check_output(
                [
                    "ssh",
                    *sshOptions(node["sshKey"]),
                    f"{node['sshUser']}@{node['ip']}",
                    command,
                ],
                stdin=subprocess.DEVNULL,
                text=True,
                stderr=subprocess.STDOUT,
            )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Could not detect underlay interface for {node['name']} via route to {peer_ip}. "
            f"Command output: {(exc.output or '').strip()!r}. "
            "Set fabric.nodes.<node>.underlayInterface explicitly."
        ) from exc
    underlay = parseRouteInterface(output, node["name"], peer_ip)
    validateInterfaceName(underlay, f"fabric.nodes.{node['name']}.underlayInterface")
    return underlay


def fabricNodeRows(data: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return per-node rows consumed by VXLAN fabric shell scripts.

    Args:
        data: Parsed configK3s.yaml mapping.
        nodes: Normalized K3s node list.

    The user may set fabric.nodes.<node>.underlayInterface explicitly. If it is
    omitted, the helper detects the underlay by asking the node which interface
    it uses to route to the peer management IP. Test IPs are internal defaults
    and are only used by validateLinuxVxlanFabric.py.
    """
    values = fabricValues(data)
    if values["fabricType"] == "none":
        return []
    if values["fabricType"] != "linux-vxlan":
        return []
    if len(nodes) != 2:
        raise SystemExit("fabric.type=linux-vxlan currently supports exactly two nodes")
    rows: list[dict[str, Any]] = []
    fabric_nodes = getNested(data, "fabric.nodes", {})
    if fabric_nodes is None:
        fabric_nodes = {}
    if not isinstance(fabric_nodes, dict):
        raise SystemExit("fabric.nodes must be a mapping keyed by node name or node IP")
    defaults = [
        ("172.31.252.1/30", "172.31.253.1/30"),
        ("172.31.252.2/30", "172.31.253.2/30"),
    ]
    for index, node in enumerate(nodes):
        node_cfg = fabric_nodes.get(node["name"]) or fabric_nodes.get(node["ip"]) or {}
        if not isinstance(node_cfg, dict):
            raise SystemExit(f"fabric.nodes.{node['name']} must be a mapping")
        peer = nodes[1 - index]
        underlay = str(node_cfg.get("underlayInterface") or node_cfg.get("underlay_interface") or "")
        if not underlay:
            underlay = detectUnderlayInterface(node, peer["ip"])
        validateInterfaceName(underlay, f"fabric.nodes.{node['name']}.underlayInterface")
        rows.append(
            {
                "name": node["name"],
                "role": node["role"],
                "ip": node["ip"],
                "connection": node["connection"],
                "sshUser": node["sshUser"],
                "sshKey": node["sshKey"],
                "underlayInterface": underlay,
                "bridgeTestIp": str(node_cfg.get("bridgeTestIp") or node_cfg.get("bridge_test_ip") or defaults[index][0]),
                "macvlanTestIp": str(node_cfg.get("macvlanTestIp") or node_cfg.get("macvlan_test_ip") or defaults[index][1]),
                "peerName": peer["name"],
                "peerIp": peer["ip"],
            }
        )
    return rows


def commandFabricShellVars(args: argparse.Namespace) -> None:
    """Print shell assignments for the optional physical L2 fabric."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    values = fabricValues(data)
    rows = fabricNodeRows(data, nodes)
    values["fabricNodeCount"] = len(rows)
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def commandOvnShellVars(args: argparse.Namespace) -> None:
    """Print shell assignments for Kube-OVN non-primary CNI install scripts."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    values = ovnValues(data, nodes)
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def commandFabricNodesTsv(args: argparse.Namespace) -> None:
    """Print per-node fabric rows as TSV for shell scripts."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    for row in fabricNodeRows(data, nodes):
        print(
            "\t".join(
                str(row[key])
                for key in (
                    "name",
                    "role",
                    "ip",
                    "connection",
                    "sshUser",
                    "sshKey",
                    "underlayInterface",
                    "bridgeTestIp",
                    "macvlanTestIp",
                    "peerName",
                    "peerIp",
                )
            )
        )


def commandShellVars(args: argparse.Namespace) -> None:
    """Print local shell assignments derived from configK3s.yaml."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    for key, value in configValues(data, nodes).items():
        print(f"{key}={shlex.quote(str(value))}")


def commandNodesTsv(args: argparse.Namespace) -> None:
    """Print normalized node rows as TSV."""
    for node in yamlNodes(loadYaml(args.config)):
        print(
            "\t".join(
                str(node[key])
                for key in ("name", "role", "ip", "mac", "vcpus", "memoryMb", "diskGb")
            )
        )


def commandNodeSshVars(args: argparse.Namespace) -> None:
    """Print shell assignments for one node's SSH settings."""
    nodes = yamlNodes(loadYaml(args.config))
    selected = next((node for node in nodes if node["name"] == args.name), None)
    if selected is None:
        raise SystemExit(f"Node not found in configK3s.yaml: {args.name}")
    print(f"nodeSshUser={shlex.quote(str(selected['sshUser']))}")
    print(f"nodeSshKey={shlex.quote(str(selected['sshKey']))}")
    print(f"nodeConnection={shlex.quote(str(selected['connection']))}")


def ansibleHostVars(node: dict[str, Any], k3s_role: str, as_group: str) -> dict[str, Any]:
    """Return Ansible host variables for one K3s node.

    Args:
        node: Normalized node dictionary from yamlNodes().
        k3s_role: K3s role string consumed by ansible/k3s-install.yml.
        as_group: Human-readable grouping label.
    """
    payload: dict[str, Any] = {"k3s_role": k3s_role, "seedemu_as_group": as_group}
    if node["connection"] == "local":
        payload.update(
            {
                "ansible_host": node["ip"],
                "ansible_connection": "local",
                "ansible_python_interpreter": "/usr/bin/python3",
            }
        )
    else:
        payload.update(
            {
                "ansible_host": node["ip"],
                "ansible_user": node["sshUser"],
                "ansible_ssh_private_key_file": node["sshKey"],
            }
        )
    return payload


def commandWriteAnsibleInventory(args: argparse.Namespace) -> None:
    """Write the temporary Ansible inventory used by applyK3sCluster.py."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    vals = configValues(data, nodes)
    master = masterNode(nodes)
    workers = [node for node in nodes if node["role"] == "worker"]
    payload = {
        "all": {
            "vars": {
                "k3s_version": vals["k3sVersion"],
                "k3s_install_version": vals["k3sInstallVersion"],
                "seed_registry_host": vals["registryHost"],
                "seed_registry_port": int(vals["registryPort"]),
                "seed_docker_io_mirror_endpoint": vals["dockerIoMirrorEndpoint"],
                "seed_k3s_artifact_url": vals["k3sArtifactUrl"],
                "seed_cni_master_interface": vals["cniMasterInterface"],
                "seed_k3s_cluster_cidr": vals["k3sClusterCidr"],
                "seed_k3s_service_cidr": vals["k3sServiceCidr"],
                "seed_k3s_flannel_backend": vals["k3sFlannelBackend"],
                "seed_k3s_node_cidr_mask_size_ipv4": int(vals["k3sNodeCidrMaskSizeIpv4"]),
                "seed_k3s_max_pods": int(vals["k3sMaxPods"]),
                "seed_k3s_expected_ready_nodes": len(nodes),
                "seed_k3s_force_reinstall": str(vals["k3sForceReinstall"]).lower() == "true",
            },
            "children": {
                "master": {
                    "hosts": {
                        master["name"]: ansibleHostVars(master, "server", "master")
                    }
                },
                "workers": {
                    "hosts": {
                        node["name"]: ansibleHostVars(node, "agent", f"worker-{index}")
                        for index, node in enumerate(workers, start=1)
                    }
                },
            },
        }
    }
    _writeYaml(args.output, payload)
    print(args.output)


def commandWriteClusterInventory(args: argparse.Namespace) -> None:
    """Write a persistent human-readable cluster inventory YAML."""
    data = loadYaml(args.config)
    nodes = yamlNodes(data)
    vals = configValues(data, nodes)
    payload = {
        "clusterName": vals["clusterName"],
        "runtime": "k3s",
        "k3s": {
            "clusterCidr": vals["k3sClusterCidr"],
            "serviceCidr": vals["k3sServiceCidr"],
            "flannelBackend": vals["k3sFlannelBackend"],
            "nodeCidrMaskSizeIpv4": int(vals["k3sNodeCidrMaskSizeIpv4"]),
            "maxPods": int(vals["k3sMaxPods"]),
        },
        "registry": {"host": vals["registryHost"], "port": int(vals["registryPort"])},
        "nodes": [
            {
                "name": node["name"],
                "role": node["role"],
                "managementIp": node["ip"],
                "connection": node["connection"],
                "ssh": {"user": node["sshUser"], "key": node["sshKey"]},
                "resources": {
                    "vcpus": node["vcpus"],
                    "memoryMb": node["memoryMb"],
                    "diskGb": node["diskGb"],
                },
                "labels": {"kubernetes.io/hostname": node["name"]},
            }
            for node in nodes
        ],
    }
    _writeYaml(vals["outputInventory"], payload)
    print(vals["outputInventory"])


def commandWriteRunningConfig(args: argparse.Namespace) -> None:
    """Write legacy configRunning.yaml for running/Makefile.

    Args:
        args.config: Source configK3s.yaml path.
        args.output_dir: Optional compile output directory.
        args.image_registry_prefix: Logical image prefix in k8s.yaml.
        args.rollout_timeout_seconds: Rollout wait timeout for make up/wait.
    """
    data = loadYaml(args.config)
    output_dir = args.output_dir or str(SETUP_DIR.parent / "emulate" / "output")
    output_path = expandPath(str(getNested(data, "outputs.runningConfig", SETUP_DIR / "configRunning.yaml")))
    payload = {
        "setupConfig": str(Path(args.config).expanduser().resolve()),
        "outputDir": expandPath(output_dir),
        "imageRegistryPrefix": args.image_registry_prefix,
        "rolloutTimeoutSeconds": int(args.rollout_timeout_seconds),
    }
    _writeYaml(output_path, payload)
    print(output_path)


def _writeYaml(path: str, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _snakeCase(value: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", r"_\1", value).lower()


def _camelCase(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="configK3s.yaml path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("shell-vars").set_defaults(func=commandShellVars)
    sub.add_parser("nodes-tsv").set_defaults(func=commandNodesTsv)
    node_ssh = sub.add_parser("node-ssh-vars")
    node_ssh.add_argument("--name", required=True)
    node_ssh.set_defaults(func=commandNodeSshVars)

    sub.add_parser("fabric-shell-vars").set_defaults(func=commandFabricShellVars)
    sub.add_parser("fabric-nodes-tsv").set_defaults(func=commandFabricNodesTsv)
    sub.add_parser("ovn-shell-vars").set_defaults(func=commandOvnShellVars)

    ansible = sub.add_parser("write-ansible-inventory")
    ansible.add_argument("--output", required=True)
    ansible.set_defaults(func=commandWriteAnsibleInventory)

    cluster = sub.add_parser("write-cluster-inventory")
    cluster.set_defaults(func=commandWriteClusterInventory)

    running = sub.add_parser("write-running-config")
    running.add_argument("--output-dir")
    running.add_argument("--image-registry-prefix", default="seedemu")
    running.add_argument("--rollout-timeout-seconds", default="1800")
    running.set_defaults(func=commandWriteRunningConfig)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
