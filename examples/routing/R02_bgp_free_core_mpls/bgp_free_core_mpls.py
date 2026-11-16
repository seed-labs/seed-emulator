#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Mpls, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a BGP-free core MPLS regression emulator.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def connect(transit_as, routers: Dict[str, object], left: str, right: str) -> None:
    network = "net_{}_{}".format(left, right)
    transit_as.createNetwork(network)
    routers[left].joinNetwork(network)
    routers[right].joinNetwork(network)


def make_mpls_slice(
    emu: Emulator,
    base: Base,
    ebgp: Ebgp,
    asn: int,
    left_ix: int,
    right_ix: int,
    left_stub: int,
    right_stub: int,
    ibgp_mode: str,
    rr_cluster: Optional[str] = None,
    rr_router: Optional[str] = None,
) -> None:
    base.createInternetExchange(left_ix)
    base.createInternetExchange(right_ix)

    transit_as = base.createAutonomousSystem(asn)
    routers = {
        "edge0": transit_as.createRouter("edge0", routingBackend="frr").joinNetwork("ix{}".format(left_ix)),
        "core0": transit_as.createRouter("core0", routingBackend="frr"),
        "core1": transit_as.createRouter("core1", routingBackend="frr"),
        "edge1": transit_as.createRouter("edge1", routingBackend="frr").joinNetwork("ix{}".format(right_ix)),
    }

    connect(transit_as, routers, "edge0", "core0")
    connect(transit_as, routers, "core0", "core1")
    connect(transit_as, routers, "core1", "edge1")

    transit_as.setIbgpMode(ibgp_mode)
    transit_as.setBgpScope("edge-only")
    transit_as.setCoreForwarding("mpls")
    routers["edge0"].setBgpRole("edge")
    routers["edge1"].setBgpRole("edge")
    routers["core0"].setBgpRole("core")
    routers["core1"].setBgpRole("core")

    if ibgp_mode == "route-reflector":
        cluster_id = rr_cluster or "10.{}.0.1".format(asn)
        reflector = rr_router or "edge0"
        transit_as.createBgpCluster(cluster_id)
        for name in ["edge0", "edge1"]:
            routers[name].joinBgpCluster(cluster_id)
            if name == reflector:
                routers[name].makeRouteReflector()

    Makers.makeStubAsWithHosts(emu, base, left_stub, left_ix, 1)
    Makers.makeStubAsWithHosts(emu, base, right_stub, right_ix, 1)
    ebgp.addPrivatePeering(left_ix, asn, left_stub, PeerRelationship.Provider)
    ebgp.addPrivatePeering(right_ix, asn, right_stub, PeerRelationship.Provider)


def build_emulator() -> Emulator:
    emu = Emulator()
    base = Base()
    ebgp = Ebgp()
    mpls = Mpls()

    make_mpls_slice(
        emu, base, ebgp,
        asn=8,
        left_ix=112,
        right_ix=113,
        left_stub=162,
        right_stub=163,
        ibgp_mode="full-mesh",
    )

    make_mpls_slice(
        emu, base, ebgp,
        asn=9,
        left_ix=114,
        right_ix=115,
        left_stub=164,
        right_stub=165,
        ibgp_mode="route-reflector",
        rr_cluster="10.9.0.1",
        rr_router="edge0",
    )

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    emu.addLayer(mpls)
    return emu


def main() -> int:
    args = parse_args()
    emu = build_emulator()

    if args.dumpfile:
        emu.dump(args.dumpfile)
        print("Saved BGP-free core MPLS emulator to {}".format(args.dumpfile))
        return 0

    if args.render:
        emu.render()

    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    docker = Docker(platform=resolve_platform(args.platform))
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, str(output_dir), override=args.override)
    print("Generated BGP-free core MPLS Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())