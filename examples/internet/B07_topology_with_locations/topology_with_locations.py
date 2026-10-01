#!/usr/bin/env python3
"""Generate transit and stub ASes with two hosts per IX (500 total nodes)."""

from __future__ import annotations

import argparse
from collections import Counter
from ipaddress import IPv4Network
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import random
import sys
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.utilities import Makers
from geopy.distance import geodesic
from seedemu.visualizationTools import visualization_manager

# The supplied catalogue is named cityies.py, not cities.py.
from cityies import IX_LOCATIONS

META = "org.seedsecuritylabs.seedemu.meta."
HOSTS_PER_STUB = 2
STUB_ASNS = {ix: 150 + ix - 100 for ix in range(100, 120)}
STUB_NODE_COUNT = len(STUB_ASNS) * (1 + HOSTS_PER_STUB)
MIN_NODE_COUNT = 58 + STUB_NODE_COUNT
# Conservative core exclusions; populated peripheral cities remain eligible.
# south, north, west, east
DESERT_CORES = [
    (19, 29, -12, 32),
    (19, 24, 44, 55),
    (37, 41, 77, 89),
    (42, 46, 95, 110),
    (39, 44, 54, 64),
    (-26, -19, 13, 16),
    (-27, -20, 19, 24),
    (-26, -20, -70, -67),
    (-30, -20, 120, 140),
]


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (a[3], a[4], b[3], b[4]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 12742 * asin(sqrt(min(1.0, max(0.0, h))))


def valid_land(lat, lon):
    try:
        from global_land_mask import globe
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt in this example directory first.") from exc
    return (
        -60 < lat < 66
        and -180 <= lon <= 180
        and not any(s <= lat <= n and w <= lon <= e for s, n, w, e in DESERT_CORES)
        and bool(globe.is_land(lat, lon))
    )


def load_cities():
    unique = {}
    for city in IX_LOCATIONS:
        lat, lon = city[3:5]
        if not valid_land(lat, lon):
            continue
        unique.setdefault((lat, lon), city)
    return list(unique.values())


def ix_display_locations(anchors, plans):
    """Keep IX semantics at the anchor; choose a small, land-checked display offset."""
    occupied = {tuple(round(v, 6) for v in c[3:5]) for c in anchors.values()}
    occupied.update(tuple(round(v, 6) for v in c[3:5]) for p in plans for _, c in p)
    result = {}
    for ix, city in anchors.items():
        nearest = min(distance(city, c) for p in plans for i, c in p if i == ix)
        maximum = min(2.0, nearest * 0.09)
        for scale in (1, 0.5, 0.25, 0.125, 0.0625, 0.03125):
            radius = maximum * scale
            for step in range(72):
                bearing = (ix * 137.508 + step * 5) % 360
                point = geodesic(kilometers=radius).destination(city[3:5], bearing)
                coord = (round(point.latitude, 6), round(point.longitude, 6))
                if coord in occupied or not valid_land(*coord):
                    continue
                # Sample every <=100 m to avoid hopping across coastal water.
                samples = max(2, int(radius / 0.1) + 1)
                path = [
                    geodesic(kilometers=radius * k / samples).destination(city[3:5], bearing)
                    for k in range(1, samples + 1)
                ]
                if not all(valid_land(p.latitude, p.longitude) for p in path):
                    continue
                result[ix] = (*city[:3], *coord, city[5])
                occupied.add(coord)
                break
            if ix in result:
                break
        if ix not in result:
            raise ValueError(f"Cannot find a safe local display offset for IX{ix} ({city[2]}).")
    return result


def select_anchors(cities):
    """Spread 20 IXes over six continents using farthest-point sampling."""
    quotas = {
        "North America": 3,
        "South America": 3,
        "Europe": 4,
        "Africa": 3,
        "Asia": 4,
        "Oceania": 3,
    }
    anchors = {}
    for region, count in quotas.items():
        pool = [c for c in cities if c[0] == region]
        chosen = [pool[0]]
        while len(chosen) < count:
            chosen.append(
                max(
                    (c for c in pool if c not in chosen),
                    key=lambda c: min(distance(c, p) for p in chosen),
                )
            )
        for city in chosen:
            anchors[100 + len(anchors)] = city
    return anchors


def backbone(anchors):
    """A spanning tree: exhaust same-continent edges before intercontinental ones."""
    reached = {next(iter(anchors))}
    edges = []
    while len(reached) < len(anchors):
        a, b = min(
            ((a, b) for a in reached for b in anchors if b not in reached),
            key=lambda pair: (
                anchors[pair[0]][0] != anchors[pair[1]][0],
                distance(anchors[pair[0]], anchors[pair[1]]),
                pair,
            ),
        )
        edges.append([a, b])
        reached.add(b)
    return edges


def plan_topology(node_count, cities, seed):
    if node_count < 58:
        raise ValueError("At least 58 nodes are needed for 20 connected IXes and transit routers.")
    if node_count > len(cities):
        raise ValueError(
            f"Requested {node_count} nodes; only {len(cities)} unique validated cities available."
        )
    anchors = select_anchors(cities)
    available = {
        c: min(
            (ix for ix in anchors if anchors[ix][0] == c[0]),
            key=lambda ix: distance(c, anchors[ix]),
        )
        for c in cities
        if c not in anchors.values()
    }
    region_capacity = Counter(c[0] for c in available)
    rng = random.Random(seed)
    # Cache nearest selected-point distances for efficient global dispersion.
    separation = {c: min(distance(c, a) for a in anchors.values()) for c in available}
    used = Counter()

    def take(ix):
        pool = [c for c in available if available[c] == ix]
        if not pool:
            pool = [c for c in available if c[0] == anchors[ix][0]]
        if not pool:
            raise ValueError(f"No unused land cities remain for IX{ix}. Reduce --nodes.")
        # Alternate medium and far rings where the catalogue supports them.
        medium = used[ix] % 2 == 0
        ring = [
            c
            for c in pool
            if (
                300 <= distance(c, anchors[ix]) <= 900
                if medium
                else distance(c, anchors[ix]) > 900
            )
        ]
        pool = ring or pool
        rng.shuffle(pool)
        city = max(pool, key=lambda c: separation[c])
        del available[city]
        used[ix] += 1
        for c in available:
            separation[c] = min(separation[c], distance(c, city))
        return (ix, city)

    plans = [[take(ix) for ix in edge] for edge in backbone(anchors)]
    remaining = node_count - 20 - 38
    # Add regional transit ASes; explicit LAN prefixes support ASNs above 255.
    while remaining:
        counts = Counter(available.values())
        region_remaining = Counter(c[0] for c in available)
        region_used = Counter()
        for ix, count in used.items():
            region_used[anchors[ix][0]] += count
        eligible = [ix for ix in anchors if region_remaining[anchors[ix][0]]]
        if remaining == 1:
            # Makers creates exactly one r<IX> per AS/IX: never repeat an IX.
            candidates = [
                (ix, p)
                for ix in eligible
                for p in plans
                if all(j != ix and anchors[j][0] == anchors[ix][0] for j, _ in p)
            ]
            if not candidates:
                raise ValueError(
                    "No regional Transit AS can accept another distinct IX; reduce --nodes."
                )
            ix, plan = min(
                candidates,
                key=lambda item: (
                    used[item[0]] / max(1, counts[item[0]] + used[item[0]]),
                    len(item[1]),
                    item[0],
                ),
            )
            plan.append(take(ix))
            remaining -= 1
            continue
        pairs = [
            (a, b)
            for a in eligible
            for b in eligible
            if a < b and anchors[a][0] == anchors[b][0] and region_remaining[anchors[a][0]] >= 2
        ]
        if not pairs:
            raise ValueError("Insufficient regional city pairs remain; reduce --nodes.")
        a, b = min(
            pairs,
            key=lambda p: (
                region_used[anchors[p[0]][0]]
                / min(region_capacity[anchors[p[0]][0]], node_count / 6),
                sum(used[i] / max(1, counts[i] + used[i]) for i in p),
                distance(anchors[p[0]], anchors[p[1]]),
                p,
            ),
        )
        plans.append([take(a), take(b)])
        remaining -= 2
    return anchors, plans


def set_geo(node, city, role):
    region, country, name, lat, lon, _ = city
    node.setGeo(lat, lon, name)
    for key, value in {
        "geo.lat": f"{lat:.6f}",
        "geo.lon": f"{lon:.6f}",
        "geo.city": name,
        "geo.country": country,
        "geo.region": region,
        "geo.source": "cityies-land-mask-validated",
        "topology.role": role,
    }.items():
        node.setLabel(key, value)


def plan_stubs(cities, anchors):
    """Reserve a router and two nearby, distinct land cities for each stub."""
    available = set(cities) - set(anchors.values())
    stubs = {}
    for ix, anchor in anchors.items():
        candidates = sorted(
            (c for c in available if c[0] == anchor[0]), key=lambda c: (distance(anchor, c), c)
        )
        for router in candidates:
            nearby = [
                c for c in candidates if c[1] == router[1] and 20 <= distance(router, c) <= 300
            ]
            if len(nearby) < HOSTS_PER_STUB:
                continue
            first = max(nearby, key=lambda c: (distance(router, c), c))
            others = [c for c in nearby if distance(first, c) >= 20]
            if not others:
                continue
            second = max(others, key=lambda c: (min(distance(router, c), distance(first, c)), c))
            stubs[ix] = [router, first, second]
            available.difference_update(stubs[ix])
            break
        else:
            raise ValueError(f"No unused regional city cluster for IX{ix} stub and hosts")
    return stubs


def transit_peerings(records):
    """Build a rooted provider/customer tree over existing shared IX LANs.

    RS peers export only local/customer routes, so a chain of RS peers cannot
    provide transit. Like B00, explicit Provider sessions carry full routes
    downstream and customer prefixes upstream. The first AS is the root;
    backbone records introduce every IX before regional records are attached.
    """
    root = records[0]["asn"]
    owners = {ix: root for ix in records[0]["ixes"]}
    depths = {root: 0}
    peerings = []
    for record in records[1:]:
        candidates = [
            (depths[owners[ix]], ix, owners[ix]) for ix in set(record["ixes"]) if ix in owners
        ]
        if not candidates:
            raise ValueError(f"AS{record['asn']} has no shared IX with the transit backbone")
        depth, ix, provider = min(candidates)
        customer = record["asn"]
        peerings.append((ix, provider, customer))
        depths[customer] = depth + 1
        for joined_ix in record["ixes"]:
            owners.setdefault(joined_ix, customer)
    return peerings


class TransitMakerBase:
    """Adapt the original four-argument Maker without changing SeedEMU APIs.

    The Maker only calls createAutonomousSystem, createRouter and createNetwork.
    Store the real AS in Base and supply explicit LAN prefixes through this
    small factory adapter, including for ASNs above 255.
    """

    def __init__(self, base, prefixes):
        self.base = base
        self.prefixes = prefixes

    def createAutonomousSystem(self, asn):
        return TransitMakerAs(self.base.createAutonomousSystem(asn), self.prefixes)


class TransitMakerAs:
    def __init__(self, system, prefixes):
        self.system = system
        self.prefixes = prefixes

    def createRouter(self, name):
        return self.system.createRouter(name)

    def createNetwork(self, name):
        return self.system.createNetwork(name, prefix=self.prefixes[name])


def build_emulator(seed=42, node_count=200):
    if node_count < MIN_NODE_COUNT:
        raise ValueError(
            f"At least {MIN_NODE_COUNT} nodes are needed, including 20 stubs and 40 hosts."
        )
    cities = load_cities()
    anchors = select_anchors(cities)
    stubs = plan_stubs(cities, anchors)
    reserved_cities = {c for cluster in stubs.values() for c in cluster}
    anchors, plans = plan_topology(
        node_count - STUB_NODE_COUNT, [c for c in cities if c not in reserved_cities], seed
    )
    displays = ix_display_locations(
        anchors, plans + [[(ix, c) for c in cluster] for ix, cluster in stubs.items()]
    )
    emu, base, ebgp = Emulator(), Base(), Ebgp()
    members = {ix: [] for ix in anchors}
    for ix, city in anchors.items():
        exchange = base.createInternetExchange(ix, rsAddress=f"10.{ix}.0.254")
        exchange.getPeeringLan().setDisplayName(f"{city[2]}-IX{ix}")
        server = exchange.getRouteServerNode()
        set_geo(server, displays[ix], "ix-route-server")
        server.setLabel("geo.source", "ix-display-offset-land-validated")
        server.setLabel("geo.anchor_ix", str(ix))
        server.setLabel("geo.anchor_lat", f"{city[3]:.6f}")
        server.setLabel("geo.anchor_lon", f"{city[4]:.6f}")
        server.setLabel("geo.display_offset_km", f"{distance(city, displays[ix]):.6f}")
    asns = iter(a for a in range(2, 65535) if a not in anchors and a not in STUB_ASNS.values())
    # Avoid 172.17.0.0/16 (Docker's usual default bridge). IX LANs occupy
    # 10.100..119.0.0/24 and Routing loopbacks occupy 10.0.0.0/16.
    internal_prefixes = (
        p
        for p in IPv4Network("10.128.0.0/9").subnets(new_prefix=24)
        if int(str(p.network_address).split(".")[1]) not in STUB_ASNS.values()
    )
    records = []
    for plan in plans:
        asn = next(asns)
        joined_ixes = [ix for ix, _ in plan]
        # Short local tree rather than a full mesh.
        reached = {0}
        links = []
        while len(reached) < len(plan):
            a, b = min(
                ((a, b) for a in reached for b in range(len(plan)) if b not in reached),
                key=lambda p: distance(plan[p[0]][1], plan[p[1]][1]),
            )
            links.append((joined_ixes[a], joined_ixes[b]))
            reached.add(b)
        addresses = {}
        for ix in joined_ixes:
            # .253 is reserved for the stub router and .254 for the route server.
            if len(members[ix]) >= 251:
                raise ValueError(f"IX{ix} exceeds its /24 address capacity; reduce --nodes.")
            addresses[ix] = f"10.{ix}.0.{2 + len(members[ix])}"
        maker_base = TransitMakerBase(
            base, {f"net_{a}_{b}": str(next(internal_prefixes)) for a, b in links}
        )
        Makers.makeTransitAs(maker_base, asn, joined_ixes, links)
        system = base.getAutonomousSystem(asn)
        for ix, city in plan:
            router = system.getRouter(f"r{ix}")
            # Replace the Maker's pending auto address before Base configures it.
            router.updateNetwork(f"ix{ix}", addresses[ix])
            members[ix].append(asn)
            set_geo(router, city, "transit-router")
            router.setLabel("geo.anchor_ix", str(ix))
            router.setLabel("geo.radius_km", f"{distance(city, anchors[ix]):.3f}")
        records.append({"asn": asn, "ixes": joined_ixes, "links": links, "kind": "transit"})
    for ix, peers in members.items():
        ebgp.addRsPeers(ix, list(dict.fromkeys(peers)))
    for ix, asn in STUB_ASNS.items():
        Makers.makeStubAsWithHosts(emu, base, asn, ix, HOSTS_PER_STUB)
        stub = base.getAutonomousSystem(asn)
        router = stub.getRouter("router0")
        router.updateNetwork(f"ix{ix}", f"10.{ix}.0.253")
        set_geo(router, stubs[ix][0], "stub-router")
        router.setLabel("geo.anchor_ix", str(ix))
        for index in range(HOSTS_PER_STUB):
            host = stub.getHost(f"host_{index}")
            set_geo(host, stubs[ix][index + 1], "stub-host")
            host.setLabel("geo.anchor_ix", str(ix))
            host.setLabel("geo.anchor_router", f"as{asn}/router0")
        records.append({"asn": asn, "ixes": [ix], "links": [], "kind": "stub"})
    for ix, provider, customer in transit_peerings(records):
        # Same orientation as B00: provider exports ALL routes to its customer.
        ebgp.addPrivatePeerings(ix, [provider], [customer], PeerRelationship.Provider)
    for layer in (base, Routing(), ebgp, Ibgp(), Ospf()):
        emu.addLayer(layer)
    return emu, records, members


class GeoDocker(Docker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.anchors = select_anchors(load_cities())

    def _getNetMeta(self, net):
        labels = super()._getNetMeta(net)
        scope, _, name = net.getRegistryInfo()
        if scope == "ix":
            city = self.anchors[int(name.removeprefix("ix"))]
            for key, value in zip(("geo.lat", "geo.lon"), city[3:5]):
                labels += f'            {META}{key}: "{value:.6f}"\n'
        return labels

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument(
        "--nodes",
        "--node-count",
        type=int,
        default=500,
        help=f"Total routers + IX route servers + hosts (default: 500; minimum: {MIN_NODE_COUNT}).",
    )
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    if args.nodes < MIN_NODE_COUNT:
        parser.error(f"--nodes must be at least {MIN_NODE_COUNT}")
    return args


def main():
    args = parse_args()
    emu, records, members = build_emulator(args.seed, args.nodes)
    if args.dumpfile:
        emu.dump(args.dumpfile)
        return 0
    if args.render:
        emu.render()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    geoDocker = GeoDocker(
        internetMapEnabled=False,
        platform=Platform.AMD64 if args.platform == "amd" else Platform.ARM64,
    )

    geoDocker.attachDockerhubContainer(
        visualization_manager.add_containers(
            internet_map_topology={},
            internet_map_geographic={},
        ),
        port_range=(8080, 9999),
    )
    emu.compile(geoDocker, str(output), override=args.override)

    for service in visualization_manager.getEnabled():
        if service.toCompose().get('network_mode') == 'host':
            continue
        geoDocker._log(
            f'visualization service {service.name}: '
            f'port mapping (host:container) {service.ports}'
        )

    print(
        f"Generated {args.nodes} nodes: 20 IX route servers + {args.nodes-80} transit routers"
        f" + 20 stub routers + 40 hosts, {len(records)} ASes."
    )
    print(f"Docker output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
