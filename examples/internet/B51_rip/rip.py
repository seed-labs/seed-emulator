#!/usr/bin/env python3
# encoding: utf-8
# Copy the B00 mini Internet topology and demonstrate OSPF and RIP composition.

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, Rip, PeerRelationship, Routing
from seedemu.utilities import Makers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the B51 OSPF and RIP mini Internet example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument("--backend", choices=["bird", "frr", "mixed"], default="mixed")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_emulator(hosts_per_as=2, backend="mixed") -> Emulator:
    """Build B00 with per-AS OSPF/RIP policy and an independent software backend."""
    if backend not in {"bird", "frr", "mixed"}:
        raise ValueError("backend must be bird, frr or mixed")
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

    # Make routers' IX interface addresses reachable across ASes, including
    # return paths when Linux chooses an IX address for an ordinary ping.
    for exchange in (ix100, ix101, ix102, ix103, ix104, ix105):
        exchange.getPeeringLan().setDirect(True)

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
    # Select routing software independently of the OSPF/RIP policy.
    for asn in base.getAsns():
        autonomous_system = base.getAutonomousSystem(asn)
        for name in autonomous_system.getRouters():
            selected = backend
            if backend == "mixed":
                selected = "frr" if asn == 3 or (asn, name) in {(2, "r101"), (12, "r104")} else "bird"
            autonomous_system.getRouter(name).setRoutingBackend(selected)

    ###############################################################################
    # Select IGP intent on the AS, like setCoreForwarding("mpls").
    # AS3, AS4 and AS12 retain the default OSPF mode.
    as2 = base.getAutonomousSystem(2)
    as2.setIgpMode("rip").setIgpInterfacePolicy("router-links")
    # The same interface policy applies to OSPF without changing its protocol.
    base.getAutonomousSystem(3).setIgpInterfacePolicy("router-links")
    base.getAutonomousSystem(11).setIgpMode("rip")
    for asn in (150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171):
        base.getAutonomousSystem(asn).setIgpMode("rip")
    ospf = Ospf()

    # RIP API examples: defaults < network < router < interface.
    rip = Rip().setTimers(update=5, timeout=30, garbage=20)
    rip.setDefaults(metric=1, split_horizon=True, poison_reverse=True)
    rip.setNetworkOptions(2, "net_100_101", metric=2)
    rip.setRouterOptions(2, "r101", metric=3, advertise_loopback=True)
    rip.setInterfaceOptions(2, "r101", "net_100_101", metric=4)
    rip.setNetworkOptions(2, "net_101_102", poison_reverse=False)
    rip.setNetworkOptions(150, "net0", passive=True)
    rip.markAsStub(151, "net0")

    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(ospf)
    emu.addLayer(rip)
    return emu


def buildEmulator(hostsPerAs: int = 2, backend: str = "mixed") -> Emulator:
    """Keep the existing B51 builder entry point for callers and CI checks."""
    return build_emulator(hosts_per_as=hostsPerAs, backend=backend)


def run(
    dumpfile=None,
    hosts_per_as=2,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
    backend="mixed",
):
    emu = build_emulator(hosts_per_as=hosts_per_as, backend=backend)
    if dumpfile is not None:
        # Save it to a file, so it can be used by other emulators.
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    # Use B00's ordinary address mode with the server's bridge netfilter at 0.
    docker = Docker(platform=platform)
    emu.compile(docker, output or "./output", override=override)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        output=str(output_dir),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
        backend=args.backend,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
