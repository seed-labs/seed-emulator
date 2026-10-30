# A15 Autonomous System Topology Generator

This example demonstrates `AutonomousSystemTopologyGenerator`, a NetworkX-based
helper for generating the internal topology of an autonomous system.

The example by default creates:

```text
AS2: generated transit AS
IX100, IX101, IX102: external peering LANs
AS150, AS151, AS152: stub ASes connected through AS2
```

The generated AS2 topology has eBGP routers such as `r0`, `r1`, and `r2`, plus
internal routers such as `core0` and `core1`. The example code manually
connects those eBGP routers to IXes.
Internal link network names are kept compact, such as `n_c10_c5`, because Linux
interface names inside containers must be no longer than 15 characters.

## Basic Run

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py --seed 42
```

The script writes two topology artifacts into the output folder:

```text
output/topology.json
output/topology.txt
```

These files record the generated routers, links, eBGP-to-internal attachment
mapping, seed, graph model, graph parameters, internal routing mode, and router
locations.

## Command-Line Controls

Important options:

- `--seed N`: make the random topology reproducible.
- `--asn N`: transit AS number, default `2`.
- `--ebgp-routers N`: number of eBGP routers generated for the transit AS.
- `--ixes 100,101,102`: IXes where this example manually connects the generated eBGP routers.
- `--stub-asns 150,151,152`: stub ASes connected to those IXes (by default, one stuf asn for each ix).
- `--internal-routers N`: number of generated internal routers.
- `--graph-model MODEL`: NetworkX model or alias.
- `--graph-param KEY=VALUE`: parameter passed to the graph model. Can be repeated.
- `--ebgp-attach-policy spread|round_robin|random|degree`: how eBGP routers attach to internal routers.
- `--internal-routing full-mesh|rr`: iBGP design inside the generated AS (full mesh or route reflector).
- `--route-reflector ROUTER`: route reflector router name when using `--internal-routing rr`.
- `--router-location ROUTER=LAT,LON`: known router location used to anchor generated positions. Can be repeated.
- `--no-locations`: skip location generation.

Example using a scale-free-style core:

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --seed 7 \
  --internal-routers 6 \
  --graph-model barabasi_albert \
  --graph-param m=2 \
  --ebgp-attach-policy degree
```

Example using an Erdos-Renyi graph:

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --seed 12 \
  --internal-routers 6 \
  --graph-model erdos_renyi \
  --graph-param p=0.4 \
  --ebgp-attach-policy random
```

Example with a larger AS:

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --ixes 100,101,102,103,104 \
  --stub-asns 150,151,152,153,154 \
  --ebgp-routers 5 \
  --asn 3 \
  --internal-routers 20 \
  --hosts-per-stub 2
```

Without extra options, this example keeps the default SEED `Ibgp()` behavior,
which creates full-mesh iBGP among routers in the generated transit AS.

## Internal Routing Modes

A15 can use the same generated physical topology with two different iBGP
control-plane designs.

### Full-Mesh iBGP

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --internal-routing full-mesh
```

This is the default mode. Every router in the generated AS participates in the
SEED `Ibgp()` full mesh. It is easy to understand and useful for small
topologies, but the number of iBGP sessions grows quickly as the AS gets larger.

### Route Reflector

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --internal-routing rr
```

In this mode, the example creates one BGP cluster. One generated internal router
is selected as the route reflector, and all routers in the generated AS join the
cluster as route-reflector clients. By default, the selected reflector is a
high-degree internal router, because that is usually a natural place to
centralize control-plane sessions in a generated topology.

You can choose the reflector explicitly:

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --internal-routing rr \
  --route-reflector core0
```

The selected mode is recorded in `output/topology.json` and
`output/topology.txt`, so CI logs and manual experiments can be compared later.

## Location Generation

A15 keeps topology generation and location generation separate. The topology
generator first creates routers and links. After that, the example uses
`AutonomousSystemLocationGenerator` to assign positions to all routers.

Known router locations are fixed. Missing router locations are generated with
NetworkX `spring_layout`, using the fixed routers as anchors. This means the
known eBGP locations stay where the user put them, while internal routers are
placed in positions that are consistent with the graph structure.

By default, this example anchors `r0`, `r1`, and `r2` to sample city locations:

```text
r0: New York
r1: Chicago
r2: Los Angeles
```

You can override or add anchors:

```sh
python examples/basic/A15_toplogy_generator/topology_generator.py \
  --router-location r0=40.7128,-74.0060 \
  --router-location r1=41.8781,-87.6298 \
  --router-location r2=34.0522,-118.2437
```

The generated locations are written to `output/topology.json` under
`locations`. They are metadata only; they do not change links, routing, BGP
sessions, OSPF, or Docker network generation.

The example also stores the coordinates on each generated router node with
`setGeo()` and `setLabel()`. The Docker compiler writes those labels into
`output/docker-compose.yml`:

```yaml
org.seedsecuritylabs.seedemu.meta.geo.lat: "40.712800"
org.seedsecuritylabs.seedemu.meta.geo.lon: "-74.006000"
org.seedsecuritylabs.seedemu.meta.geo.source: "fixed"
org.seedsecuritylabs.seedemu.meta.geo.label: "New York"
```

## Code Pattern

The core pattern is the following. The generator first creates a reusable topology object. The topology can be validated, exported, and inspected. 

```python
topology = AutonomousSystemTopologyGenerator(
    ebgp_router_count=args.ebgp_routers,
    internal_router_count=args.internal_routers,
    graph_model=args.graph_model,
    graph_params=args.graph_params,
    ebgp_attach_policy=args.ebgp_attach_policy,
    seed=args.seed,
).generate()

transit_as = base.createAutonomousSystem(args.asn)
routers = {name: transit_as.createRouter(name) for name in topology.routers()}

for ebgp_router, ix in zip(topology.ebgp_routers(), args.ixes):
    routers[ebgp_router].joinNetwork(f"ix{ix}")

for left, right, network in topology.link_networks():
    transit_as.createNetwork(network)
    routers[left].joinNetwork(network)
    routers[right].joinNetwork(network)

if args.internal_routing == "rr":
    cluster_id = "10.2.0.1"
    transit_as.createBgpCluster(cluster_id)
    for router_name in topology.routers():
        router = transit_as.getRouter(router_name).joinBgpCluster(cluster_id)
        if router_name == "core0":
            router.makeRouteReflector()

locations = AutonomousSystemLocationGenerator(
    fixed_locations={
        "r0": {"lat": 40.7128, "lon": -74.0060},
        "r1": {"lat": 41.8781, "lon": -87.6298},
        "r2": {"lat": 34.0522, "lon": -118.2437},
    },
    seed=args.seed,
).generate(topology)

for router_name, location in locations.items():
    router = transit_as.getRouter(router_name)
    router.setGeo(location["lat"], location["lon"])
    router.setLabel("geo.lat", str(location["lat"]))
    router.setLabel("geo.lon", str(location["lon"]))
    router.setLabel("geo.source", location["source"])
```




## TestRunner Lifecycle

Run from the repository root:

```sh
python seedemu/testing/cli.py clean examples/basic/A15_toplogy_generator/example.yaml
python seedemu/testing/cli.py compile examples/basic/A15_toplogy_generator/example.yaml
python seedemu/testing/cli.py build examples/basic/A15_toplogy_generator/example.yaml
python seedemu/testing/cli.py all examples/basic/A15_toplogy_generator/example.yaml
```

The runtime test checks that generated AS2 routers start BIRD, that the edge
routers receive generated eBGP peerings, and that traffic can cross the
generated AS2 transit topology from AS150 to AS152.
