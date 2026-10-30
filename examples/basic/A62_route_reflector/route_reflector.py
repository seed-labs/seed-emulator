#!/usr/bin/env python3
# encoding: utf-8
#
# Purpose: build the A62 IPv4/BIRD Route Reflector mini-Internet example.
# Inputs are standard TestRunner CLI arguments. Outputs are Docker compiler
# files under --output. Run from the repository root or this example directory.

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers
from seedemu.containerBundle import InternetMap


AS12_CLUSTER_ID = "10.12.0.1"
AS3_WEST_CLUSTER_ID = "10.3.0.1"
AS3_EAST_CLUSTER_ID = "10.3.0.2"
AS3_WEST_CLIENTS = ["r105", "r110", "r111"]
AS3_EAST_CLIENTS = ["r104", "r112", "r113"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A62 Route Reflector mini Internet example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def make_as3_route_reflector_transit(base: Base):
    """Create the larger AS3 topology used to demonstrate RR scaling."""
    as3 = base.createAutonomousSystem(3)

    border_routers = {
        100: as3.createRouter("r100").joinNetwork("ix100"),
        103: as3.createRouter("r103").joinNetwork("ix103"),
        104: as3.createRouter("r104").joinNetwork("ix104"),
        105: as3.createRouter("r105").joinNetwork("ix105"),
    }
    routers = {
        "r100": border_routers[100],
        "r103": border_routers[103],
        "r104": border_routers[104],
        "r105": border_routers[105],
        "r110": as3.createRouter("r110"),
        "r111": as3.createRouter("r111"),
        "r112": as3.createRouter("r112"),
        "r113": as3.createRouter("r113"),
    }

    for left, right in [
        ("r100", "r105"),
        ("r100", "r110"),
        ("r100", "r111"),
        ("r100", "r103"),
        ("r103", "r104"),
        ("r103", "r112"),
        ("r103", "r113"),
        ("r105", "r103"),
        ("r111", "r112"),
    ]:
        network = "net_{}_{}".format(left[1:], right[1:])
        as3.createNetwork(network)
        routers[left].joinNetwork(network)
        routers[right].joinNetwork(network)

    return as3


def build_mini_internet(emu: Emulator, base: Base, ebgp: Ebgp, hosts_per_as: int):
    """Create the B00-style mini Internet and add selected RR metadata."""
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    ix100.getPeeringLan().setDisplayName("NYC-100")
    ix101.getPeeringLan().setDisplayName("San Jose-101")
    ix102.getPeeringLan().setDisplayName("Chicago-102")
    ix103.getPeeringLan().setDisplayName("Miami-103")
    ix104.getPeeringLan().setDisplayName("Boston-104")
    ix105.getPeeringLan().setDisplayName("Houston-105")

    Makers.makeTransitAs(
        base,
        2,
        [100, 101, 102, 105],
        [(100, 101), (101, 102), (100, 105)],
    )
    make_as3_route_reflector_transit(base)
    Makers.makeTransitAs(
        base,
        4,
        [100, 102, 104],
        [(100, 104), (102, 104)],
    )

    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])

    # AS2 keeps the legacy full-mesh iBGP behavior.

    # AS12 demonstrates a single Route Reflector and one client.
    as12 = base.getAutonomousSystem(12)
    as12.setIbgpMode("route-reflector")
    as12.createBgpCluster(AS12_CLUSTER_ID)
    as12.getRouter("r101").joinBgpCluster(AS12_CLUSTER_ID).makeRouteReflector()
    as12.getRouter("r104").joinBgpCluster(AS12_CLUSTER_ID)

    # AS3 demonstrates two RR clusters plus an RR-to-RR mesh.
    as3 = base.getAutonomousSystem(3)
    as3.setIbgpMode("route-reflector")
    as3.createBgpCluster(AS3_WEST_CLUSTER_ID)
    as3.createBgpCluster(AS3_EAST_CLUSTER_ID)
    as3.getRouter("r100").joinBgpCluster(AS3_WEST_CLUSTER_ID).makeRouteReflector()
    for router in AS3_WEST_CLIENTS:
        as3.getRouter(router).joinBgpCluster(AS3_WEST_CLUSTER_ID)
    as3.getRouter("r103").joinBgpCluster(AS3_EAST_CLUSTER_ID).makeRouteReflector()
    for router in AS3_EAST_CLIENTS:
        as3.getRouter(router).joinBgpCluster(AS3_EAST_CLUSTER_ID)

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

    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])

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


def build_emulator(hosts_per_as: int = 2) -> Emulator:
    emu = Emulator()
    base = Base()
    ebgp = Ebgp()

    build_mini_internet(emu, base, ebgp, hosts_per_as)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    return emu


def run(
    dumpfile=None,
    hosts_per_as: int = 2,
    output=None,
    platform=Platform.AMD64,
    override: bool = True,
    render: bool = True,
):
    emu = build_emulator(hosts_per_as=hosts_per_as)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    docker = Docker(platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())