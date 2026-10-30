# SEED-Emulator Architecture

Orientation for an agent new to the codebase. Read [`../PRINCIPLES.md`](../PRINCIPLES.md)
first for the *why*; this file is the *what and where*. Paths are repo-root-relative.

## The emulation lifecycle: four phases

An emulation moves through four distinct phases. The first two are owned by the SDK and are
where almost all user and developer code lives; the last two are owned by the runtime.

```
  Composition  ──►  Compilation  ──►   Execution    ──►   Interaction
 (programming)     (per-backend)     (Docker/K8s/…)    (CLI / lib / AI / viz)
   SDK, layers       Compiler        container engine    InternetMap, tc, agents
   EXECUTION-AGNOSTIC │ EXECUTION-DEPENDENT
```

### 1. Composition (execution-agnostic)
Define the network in Python: build the Base topology, overlay routing, install services on
virtual nodes, set up bindings. Ends with **rendering** — `Emulator.render()` merges all layers
and resolves virtual-node bindings into a single technology-neutral intermediate representation.
Nothing here knows how the emulation will run.
- Entry object: `seedemu/core/Emulator.py` (`Emulator`).
- Building blocks: `seedemu/core/`, `seedemu/layers/`, `seedemu/services/`, `seedemu/components/`.

### 2. Compilation (execution-dependent)
A `Compiler` translates the rendered representation into concrete execution files. The *same*
rendered emulation can be handed to different compilers.
- Base class: `seedemu/core/Compiler.py`.
- Backends: `seedemu/compiler/Docker.py` (single host → `docker-compose.yml` + per-node images),
  `DistributedDocker.py`, `GcpDistributedDocker.py`, `Graphviz.py` (topology graph output).
- Call site: `emu.compile(Docker(), './output')`.

### 3. Execution
The generated files are handed to the execution engine (Docker / distributed Docker / cloud),
which builds images and starts containers. At scale this is where kernel limits bite — see
Principle 9 (RTNL contention, deferred kernel updates, multi-VM sharding).

### 4. Interaction
The live emulation is inspected and steered:
- manually via container CLIs;
- programmatically via the interaction utilities;
- visually via **InternetMap** (`tools/InternetMap2/`) — topology, node info, live packet flow,
  and controls (enter container, toggle BGP);
- at the data plane via Linux `tc` for latency/jitter/loss/bandwidth injection;
- increasingly, via AI agents (the motivation for `tools/seed-agent/`).

## The layer stack (composition model)

Layers are edited independently and merged at render (the "Photoshop" model, Principle 2).

| Category | Responsibility | Key modules |
| --- | --- | --- |
| **Base** | Structure only: ASes, IXPs, networks, routers, hosts | `seedemu/layers/Base.py`, `seedemu/core/{AutonomousSystem,InternetExchange,Network,Node}.py` |
| **Routing** | Control plane: eBGP, iBGP, OSPF, MPLS | `seedemu/layers/{Routing,Ebgp,Ibgp,Ospf,Mpls}.py` (BIRD-backed) |
| **Service** | Application plane: DNS, blockchain, CDN, Tor, PKI, … | `seedemu/services/` |
| **SCION** | Clean-slate architecture overlaid on the same base | `seedemu/layers/{ScionBase,ScionRouting,ScionIsd,Scion}.py` |

## Core abstractions (`seedemu/core/`)

The vocabulary every layer and service is built from:

- **`Emulator`** — the top-level container. Holds the layer database and binding database;
  drives `render()` and `compile()`.
- **`Layer`** — interface for a composable, mergeable layer; declares render-order dependencies.
- **`Service` / `Server`** — a pluggable application. `Service` manages installs across virtual
  nodes; `Server` is the per-node handler. `install(node)` is the core method.
- **`Component`** — a packaged, reusable sub-emulation (e.g. a whole DNS infrastructure) that
  exposes its virtual nodes via `getVirtualNodes()`.
- **`Binding` / `Filter`** — late-binding from a virtual node name to a physical node.
  `Action.{RANDOM, FIRST, LAST, NEW}`, `Filter(asn=..., nodeName=...)`.
- **`Compiler`** — translates the rendered emulation to a specific execution backend.
- **`Node`** — a physical node (router or host) with low-level APIs: `addSoftware`, `importFile`,
  `addBuildCommand`, `appendStartCommand`, `joinNetwork`.
- **`Registry`** — the shared namespace through which layers/services find each other (instead of
  poking each other directly).

## Repository map (where things live)

```
seedemu/
  core/         # the abstractions above — the contracts everything implements
  layers/       # Base, Routing (Ebgp/Ibgp/Ospf/Mpls), SCION, Dnssec, EtcHosts
  services/     # pluggable application services (one dir/file per service)
  components/   # reusable packaged sub-emulations (e.g. BgpAttackerComponent)
  compiler/     # execution backends: Docker, DistributedDocker, Gcp…, Graphviz
  generators/   # topology generation (incl. real-world / CAIDA-derived)
  mergers/      # layer-merge logic used at render
  hooks/        # render/compile hooks
  utilities/    # shared helpers

examples/       # runnable, documented scenarios — the canonical templates
  basic/        # A00…  fundamentals (simple AS, transit AS, real-world, visualization)
  internet/     # B00…  DNS, PKI, botnet, Tor, IPFS, CDN, traffic, internet map, hybrid
  blockchain/   # D00…  Ethereum PoA/PoW/PoS, Chainlink, Monero
  scion/        # S00…  SCION ISDs, SCION/BGP mixed, bandwidth tester
  yesterday_once_more/  # Y0…  historical-incident recreations (Morris, Mirai, YouTube hijack)

tools/
  InternetMap2/ # visualization web app
  DemoSystem/   # classroom/exhibition demos
  seed-agent/   # AI products: principles, knowledge, skills, agents (you are here)

docs/
  user_manual/      # how to use capabilities
  developer_manual/ # how to extend the emulator
  designs/          # design notes
```

## How a scenario flows end to end (minimal mental model)

```python
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker

emu  = Emulator()
base = Base(); routing = Routing(); ebgp = Ebgp(); ibgp = Ibgp(); ospf = Ospf()
web  = WebService()

# 1. Base: structure
base.createInternetExchange(100)
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as150.createHost('web').joinNetwork('net0')

# 2. Routing/peering: control-plane intent (relationships, not raw config)
ebgp.addRsPeers(100, [150])

# 3. Service on a virtual node + late binding to a physical node
web.install('web150')
emu.addBinding(Binding('web150', filter=Filter(asn=150, nodeName='web')))

# 4. Add layers, render (merge + resolve bindings), compile to a backend
emu.addLayer(base); emu.addLayer(routing); emu.addLayer(ebgp)
emu.addLayer(ibgp); emu.addLayer(ospf); emu.addLayer(web)
emu.render()
emu.compile(Docker(), './output')
```

Swap `Docker()` for another compiler and the first three steps are untouched — that is
Principle 1 in one diff. For the full step-by-step, see
[`../skills/seedemu-compose-scenario/SKILL.md`](../skills/seedemu-compose-scenario/SKILL.md).
