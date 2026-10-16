"""Build k8sTools input YAML with objects; no cluster or k8sTools calls occur.

Inputs are explicit Python API calls. ``compile(path)`` writes one user-input
YAML file at the caller's path and does not contact any host or cluster.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

import yaml


DEFAULT_K3S_VERSION = "v1.29.15+k3s1"
VLAN_FABRICS = {"macvlan-vlan", "bridge-vlan", "ipvlan-vlan"}


@dataclass(frozen=True)
class Ssh:
    user: str
    key: str

    def toDict(self) -> dict[str, str]:
        """Return the SSH fields expected by setup; key remains a path."""
        if not self.user or not self.key:
            raise ValueError("SSH user and key are required")
        return {"user": self.user, "key": self.key}


@dataclass(frozen=True)
class VmResources:
    vcpus: int
    memoryGiB: float
    diskGb: int

    def toDict(self) -> dict[str, int | float]:
        """Return VM resources using the accepted GiB input spelling."""
        if self.vcpus <= 0 or self.memoryGiB <= 0 or self.diskGb <= 0:
            raise ValueError("VM CPU, memory and disk must be positive")
        if not float(self.memoryGiB * 1024).is_integer():
            raise ValueError("VM memoryGiB must represent whole MiB")
        return {"vcpus": self.vcpus, "memoryGiB": self.memoryGiB, "diskGb": self.diskGb}


@dataclass(frozen=True)
class RoutedSubnet:
    cidr: str
    gateway: str
    networkName: str | None = None
    bridgeName: str | None = None
    vmIpStart: int | None = None

    def toDict(self) -> dict[str, Any]:
        """Validate a hypervisor's routed VM subnet and serialize overrides."""
        network = ip_network(self.cidr, strict=False)
        if network.version != 4 or ip_address(self.gateway) not in network:
            raise ValueError(f"gateway {self.gateway} must be inside IPv4 subnet {self.cidr}")
        result: dict[str, Any] = {"cidr": str(network), "gateway": self.gateway}
        for key in ("networkName", "bridgeName", "vmIpStart"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        if self.vmIpStart is not None and self.vmIpStart < 1:
            raise ValueError("vmIpStart must be positive")
        return result


class K8sConfig:
    """Shared configuration and YAML serialization for one deployment kind."""

    kind: str

    def __init__(self, clusterName: str):
        if not clusterName.strip():
            raise ValueError("clusterName is required")
        self._data: dict[str, Any] = {
            "kind": self.kind, "clusterName": clusterName,
            "k3s": {"version": DEFAULT_K3S_VERSION},
        }

    def setClusterName(self, name: str) -> K8sConfig:
        """Set the cluster name used in generated resources."""
        if not name.strip():
            raise ValueError("cluster name cannot be empty")
        self._data["clusterName"] = name
        return self

    def setRegistryPort(self, port: int) -> K8sConfig:
        """Override the registry port on the master node."""
        if not 1 <= port <= 65535:
            raise ValueError("registry port must be 1..65535")
        self._data.setdefault("registry", {})["port"] = port
        return self

    def setFabric(self, fabricType: str, *, masterInterface: str | None = None,
                  **options: Any) -> K8sConfig:
        """Select the fabric and derive matching CNI fields from it."""
        if fabricType not in {"none", "ovn", *VLAN_FABRICS, "linux-vxlan"}:
            raise ValueError(f"unsupported fabric type: {fabricType}")
        if fabricType in {"none", "ovn"} and masterInterface is not None:
            raise ValueError(f"fabric {fabricType} does not use masterInterface")
        if fabricType == "linux-vxlan" and masterInterface is not None and masterInterface != options.get("bridgeName", "br-seedemu"):
            raise ValueError("linux-vxlan masterInterface must match bridgeName")
        self._data["fabric"] = {**self._data.get("fabric", {}), "type": fabricType, **options}
        if fabricType in VLAN_FABRICS | {"linux-vxlan"}:
            cni_type = "macvlan" if fabricType == "linux-vxlan" else fabricType.removesuffix("-vlan")
            if fabricType == "linux-vxlan":
                parent = options.get("bridgeName", "br-seedemu")
            elif masterInterface is not None:
                parent = masterInterface
            elif self.kind == "kvm":
                parent = "ens2"
            elif self.kind == "multiHostKvm":
                parent = "ens3"
            else:
                parent = None
            cni = {"cniType": cni_type, "localLinkCniType": cni_type,
                   "attachedCniType": cni_type}
            if parent is not None:
                cni["defaultMasterInterface"] = parent
            self._data["cni"] = {**self._data.get("cni", {}), **cni}
        else:
            self._data.pop("cni", None)
        return self

    def setCni(
        self, cniType: str = "macvlan", *, masterInterface: str | None = None,
        mtu: int | None = None, localLinkCniType: str | None = None,
        attachedCniType: str | None = None,
    ) -> K8sConfig:
        """Compatibility override for callers using the older two-call API."""
        cni: dict[str, Any] = {"cniType": cniType}
        if masterInterface is not None:
            cni["defaultMasterInterface"] = masterInterface
        if mtu is not None:
            cni["mtu"] = mtu
        if localLinkCniType is not None:
            cni["localLinkCniType"] = localLinkCniType
        if attachedCniType is not None:
            cni["attachedCniType"] = attachedCniType
        self._data["cni"] = {**self._data.get("cni", {}), **cni}
        return self

    def validate(self) -> None:
        """Check cross-field constraints before writing the build input."""
        fabric = self._data.get("fabric", {})
        cni = self._data.get("cni", {})
        fabric_type = fabric.get("type", "none")
        if fabric_type in VLAN_FABRICS | {"linux-vxlan"}:
            if not cni.get("defaultMasterInterface"):
                raise ValueError(f"fabric {fabric_type} needs a CNI masterInterface")
            expected = "macvlan" if fabric_type == "linux-vxlan" else fabric_type.removesuffix("-vlan")
            for field in ("cniType", "localLinkCniType", "attachedCniType"):
                if cni.get(field, expected) != expected:
                    raise ValueError(f"cni.{field} must be {expected} for fabric {fabric_type}")
        if fabric_type == "linux-vxlan" and cni.get("defaultMasterInterface") != fabric.get("bridgeName", "br-seedemu"):
            raise ValueError("linux-vxlan CNI masterInterface must match fabric.bridgeName")
        for value in (fabric.get("mtu"), cni.get("mtu")):
            if value is not None and not 576 <= value <= 9000:
                raise ValueError("MTU must be 576..9000")
        if fabric.get("mtu") and cni.get("mtu") and fabric["mtu"] != cni["mtu"]:
            raise ValueError("fabric and CNI MTU must match when both are set")
        self._validateKind()

    def _validateKind(self) -> None:
        """Require kind-specific fields; subclasses override this hook."""
        raise NotImplementedError

    def toDict(self) -> dict[str, Any]:
        """Return a validated copy that callers can inspect or serialize."""
        self.validate()
        return deepcopy(self._data)

    def compile(self, path: str | Path) -> Path:
        """Write only the user input YAML at path and return that path."""
        output = Path(path).expanduser()
        data = self.toDict()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)
        return output


class SingleHostKvmConfig(K8sConfig):
    """Configure local libvirt VMs for one K3s cluster."""

    kind = "kvm"

    def __init__(self, clusterName: str):
        super().__init__(clusterName)
        self._data["master"] = VmResources(12, 10, 80).toDict()
        self._data["workers"] = {"count": 1, **VmResources(6, 10, 80).toDict()}

    def setVmSsh(self, ssh: Ssh) -> SingleHostKvmConfig:
        """Set the cloud-init VM login account and private key path."""
        self._data["ssh"] = ssh.toDict()
        return self

    def setMaster(self, resources: VmResources, name: str | None = None) -> SingleHostKvmConfig:
        """Override master VM size and optional VM name."""
        if "nodes" in self._data:
            raise ValueError("setMaster() cannot be combined with explicit addVm() calls")
        self._data["master"] = resources.toDict()
        if name is not None:
            self._data.setdefault("defaults", {})["masterName"] = name
        return self

    def setWorkers(self, count: int, resources: VmResources, namePrefix: str | None = None) -> SingleHostKvmConfig:
        """Override worker VM count, per-VM size and optional name prefix."""
        if "nodes" in self._data:
            raise ValueError("setWorkers() cannot be combined with explicit addVm() calls")
        if count < 0:
            raise ValueError("worker count cannot be negative")
        self._data["workers"] = {"count": count, **resources.toDict()}
        if namePrefix is not None:
            self._data.setdefault("defaults", {})["workerNamePrefix"] = namePrefix
        return self

    def addVm(self, name: str, role: str, ip: str, mac: str,
              resources: VmResources) -> SingleHostKvmConfig:
        """Use explicitly addressed VMs instead of generated master/workers."""
        if role not in {"master", "worker"}:
            raise ValueError("VM role must be master or worker")
        ip_address(ip)
        if "nodes" not in self._data:
            self._data.pop("master", None)
            self._data.pop("workers", None)
            self._data["nodes"] = []
        self._data["nodes"].append({"name": name, "role": role, "ip": ip,
                                    "mac": mac, **resources.toDict()})
        return self

    def setManagementNetwork(self, name: str, *, bridge: str | None = None,
                             cidr: str | None = None, gateway: str | None = None,
                             dhcpStart: str | None = None,
                             dhcpEnd: str | None = None) -> SingleHostKvmConfig:
        """Override the libvirt management NAT network and optional creation data."""
        kvm = self._data.setdefault("kvm", {})
        kvm["network"] = name
        for key, value in (("networkBridge", bridge), ("networkCidr", cidr),
                           ("networkGateway", gateway), ("dhcpStart", dhcpStart),
                           ("dhcpEnd", dhcpEnd)):
            if value is not None:
                kvm[key] = value
        return self

    def addExtraNetwork(self, name: str, bridge: str) -> SingleHostKvmConfig:
        """Attach an extra unnumbered libvirt network to each local VM."""
        self._data.setdefault("kvm", {}).setdefault("extraNetworks", []).append(
            {"name": name, "bridge": bridge}
        )
        return self

    def setStoragePaths(self, *, diskDir: str | None = None, baseImagePath: str | None = None,
                        cloudInitDir: str | None = None) -> SingleHostKvmConfig:
        """Override optional local KVM disk, base-image and cloud-init paths."""
        kvm = self._data.setdefault("kvm", {})
        for key, value in (("diskDir", diskDir), ("baseImagePath", baseImagePath), ("cloudInitDir", cloudInitDir)):
            if value is not None:
                kvm[key] = value
        return self

    def _validateKind(self) -> None:
        if "ssh" not in self._data:
            raise ValueError("single-host KVM requires setVmSsh()")
        if self._data.get("fabric", {}).get("type") == "linux-vxlan":
            raise ValueError("linux-vxlan fabric is for physical nodes")
        nodes = self._data.get("nodes")
        if nodes is not None:
            if sum(node["role"] == "master" for node in nodes) != 1:
                raise ValueError("explicit VMs require exactly one master")
            for field in ("name", "ip", "mac"):
                if len({node[field] for node in nodes}) != len(nodes):
                    raise ValueError(f"explicit VM {field} values must be unique")


class PhysicalHostConfig(K8sConfig):
    """Configure K3s on existing physical machines."""

    kind = "physical"

    def __init__(self, clusterName: str):
        super().__init__(clusterName)
        self._data["nodes"] = []

    def addNode(self, name: str, role: str, ip: str, *, connection: str,
                ssh: Ssh) -> PhysicalHostConfig:
        """Add an existing K3s node with explicit management access."""
        if role not in {"master", "worker"} or connection not in {"local", "ssh"}:
            raise ValueError("role must be master/worker and connection local/ssh")
        ip_address(ip)
        self._data["nodes"].append({"name": name, "role": role, "ip": ip,
                                    "connection": connection, "ssh": ssh.toDict()})
        return self

    def setNodeUnderlayInterface(self, nodeName: str, interface: str) -> PhysicalHostConfig:
        """Override the underlay NIC used by a physical linux-vxlan fabric."""
        self._data.setdefault("fabric", {}).setdefault("nodes", {}).setdefault(nodeName, {})["underlayInterface"] = interface
        return self

    def _validateKind(self) -> None:
        nodes = self._data["nodes"]
        if sum(node["role"] == "master" for node in nodes) != 1:
            raise ValueError("physical cluster requires exactly one master")
        if len({node["name"] for node in nodes}) != len(nodes) or len({node["ip"] for node in nodes}) != len(nodes):
            raise ValueError("physical node names and IPs must be unique")
        fabric = self._data.get("fabric", {})
        if fabric.get("type") == "linux-vxlan" and len(nodes) != 2:
            raise ValueError("linux-vxlan currently supports exactly two physical nodes")
        unknown = set(fabric.get("nodes", {})) - {node["name"] for node in nodes}
        if unknown:
            raise ValueError(f"underlay interface refers to unknown nodes: {sorted(unknown)}")


class MultiHostKvmConfig(K8sConfig):
    """Configure VMs distributed across physical hypervisors."""

    kind = "multiHostKvm"

    def __init__(self, clusterName: str):
        super().__init__(clusterName)
        self._data["hypervisors"] = []
        self._data["master"] = VmResources(12, 10, 80).toDict()
        self._data["workers"] = VmResources(6, 10, 80).toDict()

    def addHypervisor(self, name: str, ip: str, *, connection: str,
                      routedSubnet: RoutedSubnet, vmCount: int,
                      ssh: Ssh | None = None) -> MultiHostKvmConfig:
        """Add a host, its routed VM network and total VM capacity."""
        if connection not in {"local", "ssh"} or (connection == "ssh" and ssh is None):
            raise ValueError("remote hypervisors require SSH; connection must be local/ssh")
        if vmCount < 0:
            raise ValueError("vmCount cannot be negative")
        ip_address(ip)
        host: dict[str, Any] = {"name": name, "ip": ip, "connection": connection,
                                "routedSubnet": routedSubnet.toDict(), "vmCount": vmCount}
        if ssh is not None:
            host["ssh"] = ssh.toDict()
        self._data["hypervisors"].append(host)
        return self

    def setVmSsh(self, ssh: Ssh) -> MultiHostKvmConfig:
        """Set SSH access for VMs created on every hypervisor."""
        self._data["vmSsh"] = ssh.toDict()
        return self

    def setMaster(self, *, placement: str, resources: VmResources,
                  name: str | None = None) -> MultiHostKvmConfig:
        """Place and size the single K3s master VM."""
        self._data["master"] = {"placement": placement, **resources.toDict()}
        if name is not None:
            self._data["master"]["name"] = name
        return self

    def setWorkers(self, resources: VmResources, namePrefix: str | None = None) -> MultiHostKvmConfig:
        """Size all remaining VMs as workers and optionally name them."""
        self._data["workers"] = resources.toDict()
        if namePrefix is not None:
            self._data["workers"]["namePrefix"] = namePrefix
        return self

    def setRoutingTunnel(self, *, cidr: str, namePrefix: str = "vxkvm",
                         vniBase: int = 4280, dstPort: int = 4790) -> MultiHostKvmConfig:
        """Enable VXLAN next hops between routed hypervisor networks."""
        ip_network(cidr)
        self._data.setdefault("multiHostKvm", {})["routingTunnel"] = {
            "type": "vxlan", "namePrefix": namePrefix, "cidr": cidr,
            "vniBase": vniBase, "dstPort": dstPort,
        }
        return self

    def setFabricVxlan(self, *, vniBase: int, dstPort: int = 4789) -> MultiHostKvmConfig:
        """Override VXLAN IDs and port for cross-host VLAN trunks."""
        self._data.setdefault("multiHostKvm", {})["fabricVxlan"] = {"vniBase": vniBase, "dstPort": dstPort}
        return self

    def addVlanTrunk(self, name: str, *, masterInterface: str,
                     vlanStart: int = 1, vlanEnd: int = 4094) -> MultiHostKvmConfig:
        """Give every VM an extra NIC carrying one VLAN range."""
        trunk = {"name": name, "masterInterface": masterInterface,
                 "vlanStart": vlanStart, "vlanEnd": vlanEnd}
        self._data.setdefault("fabric", {}).setdefault("vlanTrunks", []).append(trunk)
        return self

    def _validateKind(self) -> None:
        hosts = self._data["hypervisors"]
        if not hosts or sum(host["vmCount"] for host in hosts) < 1:
            raise ValueError("multi-host KVM needs hypervisors with at least one VM")
        if "vmSsh" not in self._data:
            raise ValueError("multi-host KVM requires setVmSsh()")
        names = [host["name"] for host in hosts]
        if len(names) != len(set(names)) or len({host["ip"] for host in hosts}) != len(hosts):
            raise ValueError("hypervisor names and IPs must be unique")
        networks = [ip_network(host["routedSubnet"]["cidr"]) for host in hosts]
        if any(left.overlaps(right) for index, left in enumerate(networks) for right in networks[index + 1:]):
            raise ValueError("hypervisor routed subnets must not overlap")
        placement = self._data["master"].get("placement", names[0])
        if placement not in names or next(host for host in hosts if host["name"] == placement)["vmCount"] < 1:
            raise ValueError("master placement must name a hypervisor with at least one VM")
        fabric = self._data.get("fabric", {})
        if fabric.get("type") in {"macvlan-vlan", "bridge-vlan", "ipvlan-vlan"}:
            trunks = fabric.get("vlanTrunks", [])
            if not trunks:
                raise ValueError("multi-host VLAN fabric requires addVlanTrunk()")
            if self._data["cni"]["defaultMasterInterface"] not in {trunk["masterInterface"] for trunk in trunks}:
                raise ValueError("CNI masterInterface must match a VLAN trunk interface")
            if any(trunk["masterInterface"] == "ens2" or not 1 <= trunk["vlanStart"] <= trunk["vlanEnd"] <= 4094 for trunk in trunks):
                raise ValueError("trunks need a dedicated NIC and VLAN IDs 1..4094")
