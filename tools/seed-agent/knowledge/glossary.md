# SEED-Emulator Glossary

Concise definitions of the recurring terms in [`../PRINCIPLES.md`](../PRINCIPLES.md) and
[`architecture.md`](architecture.md). Each term notes where it lives in the code.

## Composition & lifecycle

- **Composition** — the execution-agnostic phase where you define the network in Python (the
  Base topology, routing, services, bindings). Owned by the SDK.
- **Rendering** — the final step of composition: `Emulator.render()` merges all layers and
  resolves virtual-node bindings into one technology-neutral intermediate representation.
- **Compilation** — translating the rendered representation into backend-specific execution
  files via a `Compiler`. The only execution-dependent step. (`seedemu/core/Compiler.py`)
- **Execution** — building the images and running the containers on the chosen engine
  (Docker / distributed Docker / cloud).
- **Interaction** — inspecting and steering the live emulation (CLI, interaction library,
  InternetMap, `tc`, AI agents).

## Structure (Base Layer)

- **AS (Autonomous System)** — a network under a single administrative authority, identified by
  an AS number (ASN). Created with `base.createAutonomousSystem(asn)`.
  (`seedemu/core/AutonomousSystem.py`)
- **IXP / IX (Internet Exchange Point)** — a high-throughput switch where routers from different
  ASes peer to exchange traffic. `base.createInternetExchange(n)` creates network `ixN`.
  (`seedemu/core/InternetExchange.py`)
- **Transit AS** — an AS that carries traffic for others (has internal structure and multiple
  IX connections). **Stub AS** — an edge AS that only originates/sinks its own traffic.
- **Network** — an internal subnet within an AS. `as.createNetwork('net0')`. (`seedemu/core/Network.py`)
- **Node** — a physical element: a **router** or a **host**. Low-level APIs: `joinNetwork`,
  `addSoftware`, `importFile`, `addBuildCommand`, `appendStartCommand`. (`seedemu/core/Node.py`)
- **BGP router** — a router connected to an IX; automatically configured to speak eBGP/iBGP.

## Control plane (Routing Layers)

- **BGP** — Border Gateway Protocol, the inter-domain routing protocol. **eBGP** runs between
  ASes; **iBGP** runs within an AS (full-mesh or route-reflector). (`seedemu/layers/{Ebgp,Ibgp}.py`)
- **OSPF** — intra-domain (within-AS) routing protocol; default for internal routers.
  (`seedemu/layers/Ospf.py`)
- **Peering / PeerRelationship** — a logical agreement to exchange routes. Relationships:
  `Provider` (provider–customer) and `Peer` (peer-to-peer). Set with
  `ebgp.addPrivatePeerings(ix, [provider], [customers], PeerRelationship.Provider)`.
- **Route server** — a server at an IX that redistributes routes among participants so they
  peer once with the server instead of pairwise. `ebgp.addRsPeers(ix, [asns])`.
- **BGP Large Communities** — route tags used here to encode business relationships and policy.
  (paper Appendix A.3)
- **BIRD** — the production routing daemon that backs the Routing Layer. Real software, real
  config generated from topology. (`seedemu/layers/Routing.py`)
- **Valley-free routing** — the BGP policy property that traffic follows commercially valid
  paths; physical connectivity does not imply reachability. Must be preserved by any topology
  reduction (Principle 8).

## Application plane (Service Layers)

- **Service** — a pluggable application module with a high-level API that generates real config;
  manages installs across virtual nodes. (`seedemu/core/Service.py`)
- **Server** — the per-node handler a `Service` installs. `install(node)` is its core method.
- **Component** — a reusable, packaged sub-emulation (e.g. a complete DNS infrastructure) that
  exposes virtual nodes for binding. (`seedemu/core/Component.py`)

## Binding (the portability mechanism)

- **Virtual node** — a symbolic string identifier for a service instance, decoupled from any
  physical node or IP. The "pin" on the service "chip". (Principle 4)
- **Late binding** — resolving virtual nodes to physical nodes at render time, not at definition
  time. Keeps service layers portable across topologies.
- **Binding** — the rule that maps a virtual node (by name or regex) to a physical node, via an
  `Action` and a `Filter`. (`seedemu/core/Binding.py`)
- **Action** — `RANDOM`, `FIRST`, `LAST` (pick among matching nodes) or `NEW` (create a node).
- **Filter** — selection criteria for candidate physical nodes, e.g. `Filter(asn=171,
  nodeName='web')`. (`seedemu/core/Filter.py`)

## Execution & scale

- **Compiler** — backend that turns the rendered emulation into execution files. Docker,
  DistributedDocker, GcpDistributedDocker, Graphviz. (`seedemu/compiler/`)
- **RTNL / `rtnl_lock`** — the Linux kernel's global Routing Netlink lock; the main contention
  point when many containers install routes concurrently at scale. (Principle 9)
- **Netlink storm** — the self-reinforcing feedback loop where RTNL contention starves routing
  daemons, expires timers, and triggers more route updates — preventing convergence.
- **Deferred kernel updates** — decoupling control-plane convergence from asynchronous,
  rate-controlled FIB installation, plus **jittering** to break synchronized route-install
  bursts.
- **Multi-VM deployment** — sharding the RTNL synchronization domain across multiple kernels
  (VMs), ~1,000 containers per kernel, orchestrated by the Kubernetes compiler.
- **Control-plane vs data-plane convergence** — when routing daemons have selected stable routes
  vs when the forwarding state is fully installed in the kernel FIB. The gap grows with scale.
- **Hybrid emulation** — letting emulated hosts reach the real Internet via a real-world exit
  AS/router announcing `0.0.0.0/1` + `128.0.0.0/1`. (paper Appendix A.5)

## Real-world data

- **CAIDA** — the measurement organization whose AS-relationship datasets seed real-world
  topology construction.
- **SGIM (Subgraph Generation based Influence Maximization)** — the BGP-semantics-preserving
  topology-reduction algorithm; extracts a representative subgraph that preserves eBGP sessions
  and k-core structure while keeping AS-internal integrity. (Principle 8)
- **ITIM (Internet Topology Influence Maximization)** — the problem SGIM solves: pick a seed set
  maximizing expected routing-influence spread under Internet-specific constraints.

## Tooling

- **InternetMap** — the web visualization app: topology, node info, live packet flow (via
  `tcpdump` filters), record/replay, and emulator controls. (`tools/InternetMap2/`)
- **SEED Labs** — the hands-on cybersecurity lab platform built on the emulator, used by 1200+
  institutions. (`https://seedsecuritylabs.org/`)
- **Yesterday Once More** — the initiative recreating historical Internet incidents (Morris
  worm, YouTube/Pakistan hijack, Mirai) for teaching. (`examples/yesterday_once_more/`,
  `tools/DemoSystem/`)
