#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers
from seedemu.containerBundle import InternetMap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a routing regression matrix emulator.")
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


def backend_indicator(backend: str) -> str:
    return "F" if backend == "frr" else "B"


def router_backend_map(backends: Dict[str, str]) -> Dict[str, str]:
    return {
        "edge0": backends.get("edge0", "bird"),
        "core0": backends.get("core0", "bird"),
        "core1": backends.get("core1", "bird"),
        "edge1": backends.get("edge1", "bird"),
    }


def format_router_with_backend(router_name: str, backends: Dict[str, str]) -> str:
    return "{}({})".format(router_name, backend_indicator(backends[router_name]))


def route_reflector_cluster_id(asn: int) -> str:
    return "10.{}.0.1".format(asn)


def route_reflector_summary(
    asn: int,
    backends: Dict[str, str],
    cluster_id: Optional[str],
    reflector: Optional[str],
    auto_rr: bool,
) -> Dict[str, object]:
    rr_name = "core0" if auto_rr else (reflector or "core0")
    cid = cluster_id or route_reflector_cluster_id(asn)
    members = ["edge0", "core0", "core1", "edge1"]
    return {
        "asn": asn,
        "cluster_id": cid,
        "route_reflector": rr_name,
        "clients": [router for router in members if router != rr_name],
        "backends": dict(backends),
    }


def print_route_reflector_summaries(summaries: List[Dict[str, object]]) -> None:
    if not summaries:
        return

    print("Route-reflector clusters:")
    for summary in summaries:
        backends = summary["backends"]
        clients = ",".join(
            format_router_with_backend(client, backends)
            for client in summary["clients"]
        ) or "none"
        print("  AS{} cluster {}: rr={}, clients={}".format(
            summary["asn"],
            summary["cluster_id"],
            format_router_with_backend(summary["route_reflector"], backends),
            clients,
        ))


def make_transit_slice(
    emu: Emulator,
    base: Base,
    ebgp: Ebgp,
    asn: int,
    left_ix: int,
    right_ix: int,
    left_stub: int,
    right_stub: int,
    backends: Dict[str, str],
    ibgp_mode: str,
    bgp_scope: str = "all-routers",
    rr_cluster: Optional[str] = None,
    rr_router: Optional[str] = None,
    auto_rr: bool = False,
) -> Optional[Dict[str, object]]:
    """Create one independent transit-AS regression slice."""

    base.createInternetExchange(left_ix)
    base.createInternetExchange(right_ix)

    resolved_backends = router_backend_map(backends)
    transit_as = base.createAutonomousSystem(asn)
    routers = {
        "edge0": transit_as.createRouter("edge0", routingBackend=resolved_backends["edge0"]).joinNetwork("ix{}".format(left_ix)),
        "core0": transit_as.createRouter("core0", routingBackend=resolved_backends["core0"]),
        "core1": transit_as.createRouter("core1", routingBackend=resolved_backends["core1"]),
        "edge1": transit_as.createRouter("edge1", routingBackend=resolved_backends["edge1"]).joinNetwork("ix{}".format(right_ix)),
    }

    connect(transit_as, routers, "edge0", "core0")
    connect(transit_as, routers, "core0", "core1")
    connect(transit_as, routers, "core1", "edge1")

    transit_as.setIbgpMode(ibgp_mode)
    transit_as.setBgpScope(bgp_scope)
    transit_as.setCoreForwarding("plain-ip")

    if bgp_scope == "edge-only":
        routers["edge0"].setBgpRole("edge")
        routers["edge1"].setBgpRole("edge")
        routers["core0"].setBgpRole("core")
        routers["core1"].setBgpRole("core")

    if ibgp_mode == "route-reflector" and not auto_rr:
        cluster_id = rr_cluster or "10.{}.0.1".format(asn)
        reflector = rr_router or "core0"
        transit_as.createBgpCluster(cluster_id)
        for name, router in routers.items():
            router.joinBgpCluster(cluster_id)
            if name == reflector:
                router.makeRouteReflector()

    Makers.makeStubAsWithHosts(emu, base, left_stub, left_ix, 1)
    Makers.makeStubAsWithHosts(emu, base, right_stub, right_ix, 1)
    ebgp.addPrivatePeering(left_ix, asn, left_stub, PeerRelationship.Provider)
    ebgp.addPrivatePeering(right_ix, asn, right_stub, PeerRelationship.Provider)

    if ibgp_mode == "route-reflector":
        return route_reflector_summary(asn, resolved_backends, rr_cluster, rr_router, auto_rr)
    return None


def build_emulator():
    emu = Emulator()
    base = Base()
    ebgp = Ebgp()
    rr_summaries = []

    # AS2: all-router full mesh, BIRD backend.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=2,
        left_ix=100,
        right_ix=101,
        left_stub=150,
        right_stub=151,
        backends={},
        ibgp_mode="full-mesh",
    )
    if summary:
        rr_summaries.append(summary)

    # AS3: all-router full mesh, FRR backend.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=3,
        left_ix=102,
        right_ix=103,
        left_stub=152,
        right_stub=153,
        backends={"edge0": "frr", "core0": "frr", "core1": "frr", "edge1": "frr"},
        ibgp_mode="full-mesh",
    )
    if summary:
        rr_summaries.append(summary)

    # AS4: all-router route reflector, BIRD backend.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=4,
        left_ix=104,
        right_ix=105,
        left_stub=154,
        right_stub=155,
        backends={},
        ibgp_mode="route-reflector",
        rr_cluster="10.4.0.1",
        rr_router="core0",
    )
    if summary:
        rr_summaries.append(summary)

    # AS5: all-router route reflector, FRR backend.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=5,
        left_ix=106,
        right_ix=107,
        left_stub=156,
        right_stub=157,
        backends={"edge0": "frr", "core0": "frr", "core1": "frr", "edge1": "frr"},
        ibgp_mode="route-reflector",
        rr_cluster="10.5.0.1",
        rr_router="core0",
    )
    if summary:
        rr_summaries.append(summary)

    # AS6: auto-completed RR, mixed BIRD/FRR backend.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=6,
        left_ix=108,
        right_ix=109,
        left_stub=158,
        right_stub=159,
        backends={"edge0": "bird", "core0": "frr", "core1": "bird", "edge1": "frr"},
        ibgp_mode="route-reflector",
        auto_rr=True,
    )
    if summary:
        rr_summaries.append(summary)

    # AS7: edge-only full mesh, mixed backend. This verifies BGP-free-core
    # control-plane structure without requiring plain-IP forwarding to succeed.
    summary = make_transit_slice(
        emu, base, ebgp,
        asn=7,
        left_ix=110,
        right_ix=111,
        left_stub=160,
        right_stub=161,
        backends={"edge0": "bird", "core0": "frr", "core1": "bird", "edge1": "frr"},
        ibgp_mode="full-mesh",
        bgp_scope="edge-only",
    )
    if summary:
        rr_summaries.append(summary)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    return emu, rr_summaries


def main() -> int:
    args = parse_args()
    emu, rr_summaries = build_emulator()

    if args.dumpfile:
        emu.dump(args.dumpfile)
        print("Saved routing matrix emulator to {}".format(args.dumpfile))
        print_route_reflector_summaries(rr_summaries)
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
    print_route_reflector_summaries(rr_summaries)
    print("Generated routing matrix Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())