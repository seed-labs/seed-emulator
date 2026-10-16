#!/usr/bin/env python3
"""Generate B61 deployment input YAMLs from the local object configuration API.

Edit the sample host/IP/SSH values for your lab. The only side effect is writing
three YAML files to --output-dir; this script does not build a K3s cluster.
Run from any directory with Python 3.10+ and PyYAML installed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from buildConfig import (
    MultiHostKvmConfig, PhysicalHostConfig, RoutedSubnet, SingleHostKvmConfig,
    Ssh, VmResources,
)


def createSingleHostConfig() -> SingleHostKvmConfig:
    """Create B61's local KVM input with optional VM sizing overrides."""
    return (
        SingleHostKvmConfig("seedemu-b61-kvm")
        .setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519"))
        .setMaster(VmResources(12, 10, 80), name="seedemu-b61-kvm-master")
        .setWorkers(3, VmResources(6, 10, 80), namePrefix="seedemu-b61-kvm-worker")
        .setFabric("macvlan-vlan")
    )
config=SingleHostKvmConfig("seedemu-b61-kvm")
config.setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519"))
config.setMaster(VmResources(12, 10, 80), name="seedemu-b61-kvm-master")
config.setWorkers(3, VmResources(6, 10, 80), namePrefix="seedemu-b61-kvm-worker")
config.setFabric("macvlan-vlan")
config.setCni("macvlan", masterInterface="ens2", localLinkCniType="macvlan",
        attachedCniType="macvlan")

def createPhysicalConfig() -> PhysicalHostConfig:
    """Create B61's two-node Linux VXLAN input for the sample lab."""
    return (
        PhysicalHostConfig("seedemu-b61-physical")
        .addNode("amd", "master", "10.202.236.88", connection="local",
                 ssh=Ssh("lxl", "~/.ssh/id_ed25519"))
        .addNode("idc", "worker", "10.202.191.39", connection="ssh",
                 ssh=Ssh("seed", "~/.ssh/id_ed25519"))
        .setFabric("linux-vxlan", bridgeName="br-seedemu", vxlanName="vxseed0",
                   vni=4242, dstPort=4789, mtu=1400)
        .setNodeUnderlayInterface("amd", "eno8403")
        .setNodeUnderlayInterface("idc", "enp101s0f1np1")
        .setRegistryPort(5000)
    )


def createMultiHostConfig() -> MultiHostKvmConfig:
    """Create B61's two-hypervisor KVM input and dedicated VLAN trunk."""
    return (
        MultiHostKvmConfig("seedemu-b61-multi-host-kvm")
        .addHypervisor(
            "amd", "10.202.236.88", connection="local", ssh=Ssh("lxl", "~/.ssh/id_ed25519"),
            routedSubnet=RoutedSubnet("10.80.1.0/24", "10.80.1.1",
                                      networkName="seedemu-amd", bridgeName="virbr-seed1", vmIpStart=10),
            vmCount=3,
        )
        .addHypervisor(
            "idc", "10.202.191.39", connection="ssh", ssh=Ssh("seed", "~/.ssh/id_ed25519"),
            routedSubnet=RoutedSubnet("10.80.2.0/24", "10.80.2.1",
                                      networkName="seedemu-idc", bridgeName="virbr-seed2", vmIpStart=10),
            vmCount=3,
        )
        .setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519"))
        .setMaster(placement="amd", name="seed-k3s-master", resources=VmResources(16, 32, 120))
        .setWorkers(VmResources(4, 16, 80), namePrefix="seed-k3s-worker")
        .setRoutingTunnel(cidr="10.255.80.0/24", namePrefix="vxkvm", vniBase=4280, dstPort=4790)
        .setFabricVxlan(vniBase=6100, dstPort=4789)
        .setFabric("macvlan-vlan", masterInterface="ens3", mtu=1400)
        .addVlanTrunk("trunk0", masterInterface="ens3", vlanStart=1, vlanEnd=4094)
        .setRegistryPort(5000)
    )


def generateConfigs(outputDir: Path) -> list[Path]:
    """Write three B61 build-input YAMLs under outputDir."""
    configs = (
        ("configKvmMacvlan.yaml", createSingleHostConfig()),
        ("configPhysicalMacvlan.yaml", createPhysicalConfig()),
        ("configMultiHostKvmMacvlan.yaml", createMultiHostConfig()),
    )
    return [config.compile(outputDir / filename) for filename, config in configs]


def parseArgs() -> argparse.Namespace:
    """Read the optional output directory, defaulting beside this script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "generated")
    return parser.parse_args()


if __name__ == "__main__":
    for path in generateConfigs(parseArgs().output_dir):
        print(path)
