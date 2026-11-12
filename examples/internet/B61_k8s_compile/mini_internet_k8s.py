#!/usr/bin/env python3
"""Compile a small SeedEMU Internet topology to native Kubernetes manifests.

Outputs are written to ./output by default:
- k8s.yaml: Kubernetes namespace, macvlan NetworkAttachmentDefinitions,
  and Deployments.
- images.yaml: image references and build contexts consumed by the running
  stage.
- per-node Docker build contexts and optional base_images/ contexts.
The default is macvlan+VLAN with MTU 1400: every SeedEMU network gets its own
VLAN parent subinterface. The deployment-stage YAML selects the parent
interface. Kube-OVN remains available through --cni-type kube-ovn.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import os

SCRIPT_DIR = Path(__file__).resolve().parent


def findRepoRoot(start: Path) -> Path:
    """Find the SeedEMU source tree that contains this example."""
    for candidate in (start, *start.parents):
        if (candidate / "seedemu").is_dir() and (candidate / "setup.py").is_file():
            return candidate
    raise RuntimeError(f"Cannot find SeedEMU repository root above {start}")


REPO_ROOT = findRepoRoot(SCRIPT_DIR)
sys.path = [path for path in sys.path if path != str(REPO_ROOT)]
sys.path.insert(0, str(REPO_ROOT))

from seedemu.core import Emulator
from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.utilities import Makers
from seedemu.compiler import Platform

from seedemu.compiler import KubernetesCompiler


HOSTS_PER_AS = 2
OUTPUT_DIR = Path("./output")


def parse_args() -> argparse.Namespace:
    """Parse compile options for the B61 native Kubernetes example."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for Kubernetes manifests and Docker build contexts.",
    )
    parser.add_argument(
        "--platform",
        choices=("amd64", "arm64"),
        default="amd64",
        help="Target platform for Docker build contexts.",
    )
    parser.add_argument(
        "--cni-type",
        choices=("kube-ovn", "ovn", "macvlan"),
        default="macvlan",
        help="Secondary CNI backend for SeedEMU links. Defaults to macvlan+VLAN.",
    )
    parser.add_argument(
        "--macvlan-vlan-start",
        type=int,
        default=100,
        help="First VLAN ID for --cni-type macvlan. Each SeedEMU network gets one VLAN.",
    )
    parser.add_argument(
        "--cni-mtu",
        type=int,
        default=1400,
        help="MTU for generated macvlan interfaces. Defaults to 1400.",
    )
    parser.add_argument(
        "--no-macvlan-vlan",
        action="store_true",
        help="Disable per-network VLAN subinterfaces for macvlan output.",
    )
    return parser.parse_args()


def build_emulator(hosts_per_as=2) -> Emulator:
    emu = Emulator()
    ebgp = Ebgp()
    base = Base()

    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName("NYC-100")
    ix101.getPeeringLan().setDisplayName("San Jose-101")
    ix102.getPeeringLan().setDisplayName("Chicago-102")
    ix103.getPeeringLan().setDisplayName("Miami-103")
    ix104.getPeeringLan().setDisplayName("Boston-104")
    ix105.getPeeringLan().setDisplayName("Huston-105")

    ###############################################################################
    # Create Transit Autonomous Systems

    ## Tier 1 ASes
    Makers.makeTransitAs(
        base,
        2,
        [100, 101, 102, 105],
        [(100, 101), (101, 102), (100, 105)],
    )

    Makers.makeTransitAs(
        base,
        3,
        [100, 103, 104, 105],
        [(100, 103), (100, 105), (103, 105), (103, 104)],
    )

    Makers.makeTransitAs(
        base,
        4,
        [100, 102, 104],
        [(100, 104), (102, 104)],
    )

    ## Tier 2 ASes
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])

    ###############################################################################
    # Create single-homed stub ASes.
    Makers.makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 152, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 162, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 170, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 105, hosts_per_as)

    # An example to show how to add a host with customized IP address.
    as154 = base.getAutonomousSystem(154)
    new_host = as154.createHost("host_new").joinNetwork("net0", address="10.154.0.129")
    from seedemu.core import OptionMode, OptionRegistry

    o = OptionRegistry().sysctl_netipv4_conf_rp_filter(
        {"all": False, "default": False, "net0": False},
        mode=OptionMode.RUN_TIME,
    )
    new_host.setOption(o)

    o = OptionRegistry().sysctl_netipv4_udp_rmem_min(5000, mode=OptionMode.RUN_TIME)
    new_host.setOption(o)
    # The upstream Kubernetes compiler does not translate runtime sysctl options.
    # Express this example's required settings through the portable startup API.
    new_host.appendStartCommand(
        "sysctl -w net.ipv4.conf.all.rp_filter=0 "
        "net.ipv4.conf.default.rp_filter=0 net.ipv4.udp_rmem_min=5000"
    )
    new_host.appendStartCommand("echo 0 > /proc/sys/net/ipv4/conf/net0/rp_filter")

    ###############################################################################
    # Peering via route servers.
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])

    # Private peerings for transit service.
    ebgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4], [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103, [3], [160, 161, 162], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4], [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(105, [3], [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)

    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    return emu


def configureForwardingRuntime(emulator: Emulator) -> None:
    """Disable ICMP redirects on rendered emulator's forwarding nodes.

    The upstream compiler remains unchanged. Startup commands run inside the
    privileged Pods after their secondary interfaces have been configured.
    """
    from seedemu.core.enums import NodeRole

    forwarding = {NodeRole.Router, NodeRole.BorderRouter, NodeRole.RouteServer,
                  NodeRole.OpenVpnRouter}
    for (_, kind, _), node in emulator.getRegistry().getAll().items():
        if kind in {"rnode", "rs"} and node.getRole() in forwarding:
            node.appendStartCommand(
                'for redirect_flag in /proc/sys/net/ipv4/conf/*/send_redirects; '
                'do echo 0 > "$redirect_flag"; done'
            )


def main() -> int:
    args = parse_args()

    os.chdir(SCRIPT_DIR)
    output_dir = args.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = (SCRIPT_DIR / output_dir).resolve()
    platform = Platform.AMD64 if args.platform == "amd64" else Platform.ARM64

    use_macvlan_vlan = args.cni_type == "macvlan" and not args.no_macvlan_vlan
    compiler = KubernetesCompiler(
        platform=platform,
        cni_type=args.cni_type,
        cni_mtu=args.cni_mtu,
        macvlan_vlan_mode=use_macvlan_vlan,
        macvlan_vlan_id_start=args.macvlan_vlan_start,
    )

    emu = build_emulator(hosts_per_as=HOSTS_PER_AS)
    emu.render()
    configureForwardingRuntime(emu)
    emu.compile(compiler, str(output_dir), override=True)

    print("=" * 72)
    print("Native Kubernetes baseline compilation complete.")
    print("=" * 72)
    print("Config file: not used")
    print(f"Output directory: {output_dir}")
    print("Image registry prefix: seedemu")
    print("Namespace: seedemu")
    print(f"CNI type: {args.cni_type}")
    print("CNI master interface: selected from the deployment YAML during up")
    print(f"CNI MTU: {args.cni_mtu}")
    print(f"Macvlan VLAN mode: {use_macvlan_vlan}")
    print("Runtime workflow: seedemu.k8sTools")
    print("Inventory required for compile: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
