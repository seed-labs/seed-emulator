#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, Ibgp, Mpls, Ospf, PeerRelationship, Routing
from seedemu.services import ExaBgpService, WebService
from seedemu.containerBundle import InternetMap


AS3_CLUSTER_ID = "10.3.0.1"
EXABGP_PREFIX = "198.51.100.0/24"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the A63 control-plane regression example.")
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


def build_route_server_slice(emu: Emulator, base: Base, ebgp: Ebgp, web: WebService) -> None:
    """Keep the legacy BIRD route-server path visible in the regression topology."""

    base.createInternetExchange(100)

    for asn in [150, 151]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork("net0")
        current_as.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
        current_as.createHost("web").joinNetwork("net0")

        vnode = "web{}".format(asn)
        web.install(vnode)
        emu.addBinding(Binding(vnode, filter=Filter(nodeName="web", asn=asn)))
        ebgp.addRsPeer(100, asn)


def build_frr_route_server_slice(emu: Emulator, base: Base, ebgp: Ebgp, web: WebService) -> None:
    """Exercise a FRR route-server IX without changing the legacy BIRD RS default."""

    ix = base.createInternetExchange(107)
    ix.getRouteServerNode().setRoutingBackend("frr")

    for asn in [157, 158]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork("net0")
        current_as.createRouter("router0").joinNetwork("net0").joinNetwork("ix107")
        current_as.createHost("web").joinNetwork("net0")

        vnode = "web{}".format(asn)
        web.install(vnode)
        emu.addBinding(Binding(vnode, filter=Filter(nodeName="web", asn=asn)))
        ebgp.addRsPeer(107, asn)


def build_mixed_backend_slice(emu: Emulator, base: Base, ebgp: Ebgp, web: WebService) -> None:
    """Exercise one transit AS with BIRD and FRR routers from shared BGP/OSPF intent."""

    base.createInternetExchange(101)
    base.createInternetExchange(102)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix101")
    as2.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("ix102")

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork("net0")
    as152.createRouter("router0", routingBackend="frr").joinNetwork("net0").joinNetwork("ix101")
    as152.createHost("web").joinNetwork("net0")
    web.install("web152")
    emu.addBinding(Binding("web152", filter=Filter(nodeName="web", asn=152)))

    as153 = base.createAutonomousSystem(153)
    as153.createNetwork("net0")
    as153.createRouter("router0").joinNetwork("net0").joinNetwork("ix102")
    as153.createHost("web").joinNetwork("net0")
    web.install("web153")
    emu.addBinding(Binding("web153", filter=Filter(nodeName="web", asn=153)))

    ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(102, 2, 153, abRelationship=PeerRelationship.Provider)


def build_frr_route_reflector_slice(base: Base, ebgp: Ebgp) -> None:
    """Validate FRR route-reflector rendering and runtime route propagation."""

    base.createInternetExchange(103)

    as3 = base.createAutonomousSystem(3)
    as3.createNetwork("net0")
    as3.setIbgpMode("route-reflector")
    as3.createBgpCluster(AS3_CLUSTER_ID)
    as3.createRouter("rr", routingBackend="frr").joinNetwork("net0").joinNetwork("ix103").joinBgpCluster(AS3_CLUSTER_ID).makeRouteReflector()
    as3.createRouter("client", routingBackend="frr").joinNetwork("net0").joinBgpCluster(AS3_CLUSTER_ID)

    as154 = base.createAutonomousSystem(154)
    as154.createNetwork("net0")
    as154.createRouter("router0").joinNetwork("net0").joinNetwork("ix103")
    as154.createHost("host").joinNetwork("net0")

    ebgp.addPrivatePeering(103, 3, 154, abRelationship=PeerRelationship.Provider)


def build_exabgp_slice(base: Base, exabgp: ExaBgpService, emu: Emulator) -> None:
    """Install ExaBGP as a Service + Binding speaker, never as a router backend."""

    base.createInternetExchange(104)

    as4 = base.createAutonomousSystem(4)
    as4.createNetwork("net0")
    as4.createRouter("router0", routingBackend="frr").joinNetwork("net0").joinNetwork("ix104")

    as180 = base.createAutonomousSystem(180)
    as180.createHost("exabgp").joinNetwork("ix104", address="10.104.0.180")

    exabgp.install("as180_exabgp") \
        .setLocalAsn(180) \
        .addPeer("router0", router_asn=4, router_relationship="customer") \
        .addAnnouncement(EXABGP_PREFIX)
    emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))


def build_mpls_readiness_slice(base: Base, ebgp: Ebgp, mpls: Mpls) -> None:
    """Keep MPLS config/readiness in scope while leaving dataplane checks host-gated."""

    base.createInternetExchange(105)
    base.createInternetExchange(106)

    as20 = base.createAutonomousSystem(20)
    as20.createNetwork("net0")
    as20.createNetwork("net1")
    as20.createNetwork("net2")
    as20.createRouter("r1", routingBackend="frr").joinNetwork("net0").joinNetwork("ix105")
    as20.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("net1")
    as20.createRouter("r3", routingBackend="frr").joinNetwork("net1").joinNetwork("net2")
    as20.createRouter("r4", routingBackend="frr").joinNetwork("net2").joinNetwork("ix106")
    as20.setCoreForwarding("mpls")

    as155 = base.createAutonomousSystem(155)
    as155.createNetwork("net0")
    as155.createRouter("router0").joinNetwork("net0").joinNetwork("ix105")

    as156 = base.createAutonomousSystem(156)
    as156.createNetwork("net0")
    as156.createRouter("router0").joinNetwork("net0").joinNetwork("ix106")

    ebgp.addPrivatePeering(105, 20, 155, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(106, 20, 156, abRelationship=PeerRelationship.Provider)


def build_emulator() -> Emulator:
    emu = Emulator()

    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    ebgp = Ebgp()
    mpls = Mpls()
    exabgp = ExaBgpService()
    web = WebService()

    build_route_server_slice(emu, base, ebgp, web)
    build_frr_route_server_slice(emu, base, ebgp, web)
    build_mixed_backend_slice(emu, base, ebgp, web)
    build_frr_route_reflector_slice(base, ebgp)
    build_exabgp_slice(base, exabgp, emu)
    build_mpls_readiness_slice(base, ebgp, mpls)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(ebgp)
    emu.addLayer(mpls)
    emu.addLayer(exabgp)
    emu.addLayer(web)
    return emu


def main() -> int:
    args = parse_args()
    emu = build_emulator()

    if args.dumpfile:
        emu.dump(args.dumpfile)
        print("Saved A63 emulator to {}".format(args.dumpfile))
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
    print("Generated A63 Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())