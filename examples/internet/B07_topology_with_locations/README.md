# Topology with Geographic Locations

This example generates a configurable SeedEMU topology with 20 Internet exchanges (IXes), transit autonomous systems (ASes), and 20 stub ASes with two hosts each. It includes topology and geographic map services for viewing the emulation.

## Generate and run

Use Python 3.10 or later with this repository's SeedEMU dependencies installed, including `geopy`. Install the additional example dependencies and generate the default topology from the repository root:

```sh
python -m pip install -r examples/internet/B07_topology_with_locations/requirements.txt
python examples/internet/B07_topology_with_locations/topology_with_locations.py --nodes 200
```

The default is **500 emulated nodes**, seed `42`, and the `amd` platform. Output is written to this example's `output` directory, regardless of the working directory.

Start the generated environment on a Docker host with Docker Compose:

```sh
docker compose -f examples/internet/B07_topology_with_locations/output/docker-compose.yml up -d --build
docker compose -f examples/internet/B07_topology_with_locations/output/docker-compose.yml ps
```

The attached services are:

| Service | Purpose |
| --- | --- |
| `seedemu_internet_map_toplogy` | Topology map; the service name uses this spelling in the compiler |
| `seedemu_internet_map_geographic` | Geographic map |
| `seedemu_emulator_service` | Backend shared by the maps |
| `seedemu_traffic_observer_service` | Traffic observation backend used by the geographic map |

The compiler selects available host ports in **8080–9999** for services that use port mappings. Read the generated Compose file or `docker compose ps` output to find each map's host port, then open `http://localhost:<port>` on the Docker host (or substitute the host's address). Ports are selected during generation, so they must also be available on the deployment host.

The traffic observer uses host networking, the host PID namespace, privileged mode, and Linux kernel/BPF mounts. Run the full environment on a Linux Docker host that supports these facilities. The legacy built-in Internet map is disabled with `internetMapEnabled=False`; the map containers above are attached separately with `attachDockerhubContainer()`.

To regenerate and rebuild an existing deployment, for example with 600 nodes:

```sh
python examples/internet/B07_topology_with_locations/topology_with_locations.py --nodes 600
docker compose -f examples/internet/B07_topology_with_locations/output/docker-compose.yml up -d --build --force-recreate --remove-orphans
```

On Windows systems whose default encoding causes console errors, run the generator with `python -X utf8`.

## Command-line options

| Option | Default | Behavior |
| --- | --- | --- |
| `--nodes`, `--node-count` | `500` | Total emulated nodes, including routers, IX route servers, and hosts; minimum `118` |
| `--seed` | `42` | Seed for randomized city selection during transit planning |
| `--platform` | `amd` | Select `amd` (AMD64) or `arm` (ARM64) for the Docker compiler |
| Positional `amd` / `arm` | Unset | Legacy platform argument; an explicit `--platform` takes precedence |
| `--output` | `output` under this example directory | Docker compiler output directory; explicit relative paths resolve from the working directory |
| `--dumpfile` | Unset | Save the constructed emulator and exit before rendering, compilation, visualization attachment, or Compose validation |
| `--override` | Enabled | Allow replacement of an existing output directory |
| `--no-override` | Disabled | Refuse to overwrite an existing output directory |
| `--skip-render` | Disabled | Skip rendering before compilation; unsuitable for the normal CLI workflow, which constructs a fresh emulator |

Examples, run from the repository root:

```sh
python examples/internet/B07_topology_with_locations/topology_with_locations.py --nodes 600 --platform arm --output ./output-600
python examples/internet/B07_topology_with_locations/topology_with_locations.py --nodes 119 --seed 7 --output ./output-119
```

For Python callers, `build_emulator(seed=42, node_count=200)` returns `(emu, records, members)`. Its node-count default is **200**, whereas the CLI explicitly passes its default of **500**.

## Node counts and topology

For a requested total of `N` nodes:

| Node type | Count | Count at the CLI default (`N = 500`) |
| --- | --- | --- |
| IX route servers | 20 | 20 |
| Transit routers | `N - 80` | 420 |
| Stub routers | 20 | 20 |
| Stub hosts | 40 | 40 |
| Total emulated nodes | `N` | 500 |

This count excludes visualization backends, map containers, and compiler-generated image helper services. The generated Compose file therefore contains more than `N` services.

IX100–IX119 form a connected backbone with 19 transit ASes and 38 transit routers. The minimum topology has 118 nodes: these 58 backbone nodes plus 20 stub routers and 40 hosts. Additional transit ASes normally have two routers connected to distinct IXes on the same continent. An odd total adds a third router at a distinct IX to a regional transit AS. There are `floor((N - 80) / 2)` transit ASes plus 20 stub ASes: 230 ASes at 500 nodes, or 280 ASes at 600 nodes.

Each IX has one stub AS, from AS150 at IX100 through AS169 at IX119. `Makers.makeStubAsWithHosts()` creates `router0`, `host_0`, and `host_1`. Both hosts join `net0` and use the stub router as their default gateway. Stub ASes connect to an upstream provider at their IX and do not peer with the route server.

The backbone prioritizes same-continent links, with five intercontinental ASes connecting the six continents. Transit ASes use `Makers.makeTransitAs()` with routers named `r<IX>` and internal networks named `net_<IX>_<IX>`. Internal links form a distance-prioritized tree.

The maximum supported size depends on the filtered city catalogue, available regional city pairs, stub city clusters, and IX address capacity. The generator raises an error if it cannot satisfy the request; it does not fill missing locations with duplicated or randomly shifted cities.

## Geographic placement

The city catalogue is [cityies.py](./cityies.py), including the spelling of its filename. The generator deduplicates coordinates, checks land coverage with `global-land-mask`, restricts latitude to `-60 < latitude < 66`, and excludes the desert-core rectangles listed in the script.

IX anchors are selected by farthest-point sampling within each continent:

| Continent | IXes |
| --- | --- |
| North America | 3 |
| South America | 3 |
| Europe | 4 |
| Africa | 3 |
| Asia | 4 |
| Oceania | 3 |

Stub locations are reserved before transit locations. Each stub router and its two hosts occupy distinct catalogue coordinates on the IX's continent. Both hosts are in the router's country and 20–300 km from the router, with at least 20 km between hosts.

Transit routers prefer cities assigned to their nearest IX on the same continent, falling back to other available cities on that continent. Selection alternates between medium-distance candidates (300–900 km) and distant candidates (over 900 km) where available, while favoring separation from already selected locations.

The IX network retains its original city anchor for the map's star marker. Its route-server container gets a small display offset to separate it visually from the marker. The initial offset is capped at 2 km and 9% of the nearest attached node's distance; the generator tries smaller offsets if needed. It checks both the endpoint and the path at intervals of at most 100 m against the land filter.

All emulated nodes have labels under `org.seedsecuritylabs.seedemu.meta.`, including `geo.lat`, `geo.lon`, `geo.city`, `geo.country`, `geo.region`, `geo.source`, and `topology.role`. IX networks also carry `geo.lat` and `geo.lon`. Additional node labels identify IX anchors, transit-router distances, stub-host parent routers, and route-server display offsets.

These checks use a land raster and rectangular exclusions; they are not a high-resolution coastline survey. Visual placement can be inspected in the geographic map.

## Routing and addressing

Transit ASes peer with each IX's route server. Because route-server peering alone does not propagate routes through an arbitrary chain of transit ASes, the generator also builds a provider/customer tree over existing shared IXes. The first transit AS is the root. Every remaining transit or stub AS gets one upstream provider through `PeerRelationship.Provider`.

Providers export full routes downstream; customers export local and customer routes upstream. OSPF carries internal routing, and iBGP exchanges BGP routes within each transit AS. The provider tree supplies a policy path across the topology but has no redundant upstream providers.

| Network or interface | Address allocation |
| --- | --- |
| IX LAN | `10.<IX>.0.0/24`, for IX100–IX119 |
| IX route server | `10.<IX>.0.254` |
| Stub router on its IX | `10.<IX>.0.253` |
| Transit routers on an IX | Sequential addresses from `.2` through `.252` (at most 251 members) |
| Stub `net0` | `10.<stub-ASN>.0.0/24` |
| Transit internal LANs | Unique `/24` subnets from `10.128.0.0/9`, excluding `10.150.0.0/16` through `10.169.0.0/16` |
| Routing loopbacks | Allocated by the Routing layer from `10.0.0.0/16` |

`TransitMakerBase` and `TransitMakerAs` provide explicit internal prefixes to the four-argument transit Maker. IX interface addresses are set before rendering, allowing transit ASNs above 255 without using the ASN as an IPv4 octet.

## Automatic validation

After compilation, `validate_compose()` reads `docker-compose.yml` and checks:

- The exact number of emulated nodes identified by their role labels, and the expected counts for all four topology roles.
- One router and two hosts in each stub AS, with the correct IX anchor.
- Geographic coordinates for nodes and global IX networks, with catalogue membership for unshifted locations.
- Route-server anchor consistency and valid land offsets of at most approximately 2 km and less than one tenth of the nearest attached router's distance.
- Unique coordinates across all emulated nodes and exactly 20 global IX networks.

Successful generation prints the node breakdown, total AS count, and output directory. These checks validate generated metadata; they do not run containers, verify BGP convergence, or test end-to-end connectivity. This example directory currently contains no standalone connectivity checker or regression test suite.
