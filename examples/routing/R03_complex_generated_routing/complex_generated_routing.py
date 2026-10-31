#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import AutonomousSystemTopologyGenerator, Makers
from seedemu.containerBundle import InternetMap


DEFAULT_IXES = [120, 121, 122, 123]
DEFAULT_STUBS_PER_IX = 2
DEFAULT_STUB_ASN_BASE = 170


def parse_csv_ints(value: str) -> List[int]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("value must contain at least one integer")
    return [int(item) for item in items]


def parse_graph_param(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("graph parameters must use KEY=VALUE")

    key, raw_value = value.split("=", 1)
    key = key.strip()
    raw_value = raw_value.strip()
    if not key:
        raise argparse.ArgumentTypeError("graph parameter key cannot be empty")

    if raw_value.lower() in {"true", "false"}:
        return key, raw_value.lower() == "true"

    try:
        return key, int(raw_value)
    except ValueError:
        pass

    try:
        return key, float(raw_value)
    except ValueError:
        return key, raw_value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a complex generated routing regression emulator.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)

    parser.add_argument("--seed", type=int, default=73)
    parser.add_argument("--asn", type=int, default=10)
    parser.add_argument("--ixes", type=parse_csv_ints, default=DEFAULT_IXES)
    parser.add_argument("--stubs-per-ix", type=int, default=DEFAULT_STUBS_PER_IX)
    parser.add_argument("--internal-routers", type=int, default=12)
    parser.add_argument("--hosts-per-stub", type=int, default=1)
    parser.add_argument("--graph-model", default="small_world")
    parser.add_argument("--graph-param", action="append", type=parse_graph_param, default=[])
    parser.add_argument(
        "--ebgp-attach-policy",
        choices=["spread", "round_robin", "random", "degree"],
        default="degree",
    )
    parser.add_argument(
        "--ibgp-mode",
        choices=["full-mesh", "rr", "route-reflector"],
        default="full-mesh",
        help="Use all-router full mesh or route-reflector iBGP.",
    )
    parser.add_argument(
        "--rr-clusters",
        type=int,
        default=1,
        help="Number of route-reflector clusters to create in RR mode.",
    )
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    args.graph_params = dict(args.graph_param)
    if args.ibgp_mode == "route-reflector":
        args.ibgp_mode = "rr"
    if args.stubs_per_ix < 1:
        parser.error("--stubs-per-ix must be at least 1")
    if args.rr_clusters < 1:
        parser.error("--rr-clusters must be at least 1")
    args.stub_asns = allocate_stub_asns(
        total=len(args.ixes) * args.stubs_per_ix,
        reserved_asn=args.asn,
    )
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def router_backend(router_name: str, router_index: int) -> str:
    # Deterministic 50/50 split: even-numbered routers use BIRD, odd-numbered
    # routers use FRR. With an odd router count, BIRD gets one extra router.
    return "bird" if router_index % 2 == 0 else "frr"


def backend_indicator(backend: str) -> str:
    return "F" if backend == "frr" else "B"


def router_backend_map(topology) -> Dict[str, str]:
    return {
        name: router_backend(name, index)
        for index, name in enumerate(topology.routers())
    }


def format_router_with_backend(router_name: str, backend_map: Dict[str, str]) -> str:
    return "{}({})".format(router_name, backend_indicator(backend_map[router_name]))


def allocate_stub_asns(total: int, reserved_asn: int, base: int = DEFAULT_STUB_ASN_BASE) -> List[int]:
    stub_asns = []
    candidate = int(base)
    while len(stub_asns) < total:
        if candidate != int(reserved_asn):
            stub_asns.append(candidate)
        candidate += 1
    return stub_asns


def assign_stubs_to_ixes(ixes: List[int], stub_asns: List[int], stubs_per_ix: int) -> Dict[int, List[int]]:
    assignments = {}
    index = 0
    for ix in ixes:
        assignments[ix] = stub_asns[index:index + stubs_per_ix]
        index += stubs_per_ix
    return assignments


def apply_topology(base: Base, topology, asn: int, ixes: List[int]):
    transit_as = base.createAutonomousSystem(asn)
    routers = {}
    backends = router_backend_map(topology)

    for name in topology.routers():
        backend = backends[name]
        router = transit_as.createRouter(name, routingBackend=backend)
        router.setLabel("routing.example.backend_mix", "half-bird-half-frr")
        routers[name] = router

    for ebgp_router, ix in zip(topology.ebgp_routers(), ixes):
        routers[ebgp_router].joinNetwork("ix{}".format(ix))

    for left, right, network in topology.link_networks():
        transit_as.createNetwork(network)
        routers[left].joinNetwork(network)
        routers[right].joinNetwork(network)

    return transit_as


def configure_ibgp(transit_as, topology, mode: str, rr_clusters: int) -> Dict[str, Any]:
    if mode == "full-mesh":
        transit_as.setIbgpDesign(mode="full-mesh", scope="all-routers", core_forwarding="plain-ip")
        return {
            "mode": "full-mesh",
            "scope": "all-routers",
            "description": "all routers participate in a full-mesh iBGP control plane",
        }

    transit_as.setIbgpDesign(mode="route-reflector", scope="all-routers", core_forwarding="plain-ip")
    assignments = assign_route_reflector_clusters(transit_as, topology, rr_clusters)
    return {
        "mode": "route-reflector",
        "scope": "all-routers",
        "cluster_count": rr_clusters,
        "clusters": assignments,
        "description": "all routers participate in route-reflector iBGP with deterministic clusters",
    }


def assign_route_reflector_clusters(transit_as, topology, cluster_count: int) -> List[Dict[str, Any]]:
    routers = sorted(topology.routers())
    graph = topology.graph()
    cluster_count = min(cluster_count, len(routers))
    groups = [[] for _ in range(cluster_count)]

    for index, router in enumerate(routers):
        groups[index % cluster_count].append(router)

    assignments = []
    for index, group in enumerate(groups):
        cluster_id = route_reflector_cluster_id(transit_as.getAsn(), index)
        reflector = sorted(group, key=lambda router: (-graph.degree(router), router))[0]
        transit_as.createBgpCluster(cluster_id)

        for router_name in group:
            router = transit_as.getRouter(router_name).joinBgpCluster(cluster_id)
            if router_name == reflector:
                router.makeRouteReflector()

        assignments.append({
            "cluster_id": cluster_id,
            "route_reflector": reflector,
            "clients": [router for router in group if router != reflector],
            "routers": list(group),
        })

    return assignments


def route_reflector_cluster_id(asn: int, cluster_index: int) -> str:
    return "10.{}.{}.{}".format((int(asn) // 256) % 256, int(asn) % 256, cluster_index + 1)


def write_artifacts(
    topology,
    output_dir: Path,
    internal_routing: Dict[str, Any],
    stub_assignments: Dict[int, List[int]],
):
    output_dir.mkdir(parents=True, exist_ok=True)
    data = topology.to_dict()
    data["internal_routing"] = internal_routing
    data["backend_policy"] = "deterministic 50% BIRD and 50% FRR by router order"
    data["stub_assignments"] = {
        str(ix): list(stub_asns)
        for ix, stub_asns in stub_assignments.items()
    }

    with open(output_dir / "topology.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)

    with open(output_dir / "topology.txt", "w", encoding="utf-8") as file:
        file.write(topology.summary())
        file.write("\n")
        file.write("internal routing: {}\n".format(internal_routing["mode"]))
        if internal_routing["mode"] == "route-reflector":
            for cluster in internal_routing["clusters"]:
                file.write(
                    "cluster {} rr {} clients {}\n".format(
                        cluster["cluster_id"],
                        cluster["route_reflector"],
                        ",".join(cluster["clients"]),
                    )
                )


def build_emulator(args: argparse.Namespace):
    emu = Emulator()
    base = Base()
    ebgp = Ebgp()

    for ix in args.ixes:
        base.createInternetExchange(ix)

    topology = AutonomousSystemTopologyGenerator(
        ebgp_router_count=len(args.ixes),
        internal_router_count=args.internal_routers,
        graph_model=args.graph_model,
        graph_params=args.graph_params,
        ebgp_attach_policy=args.ebgp_attach_policy,
        seed=args.seed,
        ebgp_router_prefix="r",
    ).generate()

    transit_as = apply_topology(base, topology, args.asn, args.ixes)
    internal_routing = configure_ibgp(transit_as, topology, args.ibgp_mode, args.rr_clusters)
    stub_assignments = assign_stubs_to_ixes(args.ixes, args.stub_asns, args.stubs_per_ix)

    for ix, stub_asns in stub_assignments.items():
        for stub_asn in stub_asns:
            Makers.makeStubAsWithHosts(emu, base, stub_asn, ix, args.hosts_per_stub)
            ebgp.addPrivatePeering(ix, args.asn, stub_asn, PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    return emu, topology, internal_routing, stub_assignments


def main() -> int:
    args = parse_args()
    emu, topology, internal_routing, stub_assignments = build_emulator(args)

    if args.dumpfile:
        emu.dump(args.dumpfile)
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
    write_artifacts(topology, output_dir, internal_routing, stub_assignments)

    print(topology.summary())
    print("Stub ASes: {}".format(",".join(str(asn) for asns in stub_assignments.values() for asn in asns)))
    print("Backend mix: 50% BIRD / 50% FRR")
    print("Internal routing mode: {}".format(internal_routing["mode"]))
    if internal_routing["mode"] == "route-reflector":
        backends = router_backend_map(topology)
        print("Route-reflector clusters: {}".format(len(internal_routing["clusters"])))
        for cluster in internal_routing["clusters"]:
            print("  cluster {}: rr={}, clients={}".format(
                cluster["cluster_id"],
                format_router_with_backend(cluster["route_reflector"], backends),
                ",".join(format_router_with_backend(client, backends) for client in cluster["clients"]) or "none",
            ))
    print("Generated complex routing Docker output in {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())