---
name: seedemu-compose-scenario
description: Use when building a new SEED-Emulator (seedemu) emulation scenario — composing autonomous systems, Internet exchanges, networks, routers, hosts, BGP/OSPF routing, and services with the Python SDK, then rendering and compiling to Docker or a distributed backend. Covers the standard compose → render → compile → verify workflow and the design rules a scenario must follow.
---

# Compose a SEED-Emulator Scenario

Build a new emulation by composing the SDK building blocks, the way the existing `examples/`
do. This skill is the standard path for "make an emulator that has …".

## Read first

- [`../../PRINCIPLES.md`](../../PRINCIPLES.md) — especially P1 (execution-agnostic), P2 (layers),
  P3 (programmatic), P4 (virtual nodes + binding). Your scenario must obey these.
- [`../../knowledge/architecture.md`](../../knowledge/architecture.md) — the four phases and the
  end-to-end minimal example.
- [`../../knowledge/capability-map.md`](../../knowledge/capability-map.md) — to confirm a needed
  capability exists and find the closest example to copy.

Then **find the closest existing example and copy its structure** — examples are the canonical
templates:
- `examples/basic/` — fundamentals (`A00_simple_as`, `A01_transit_as`, `A03_real_world`,
  `A04_visualization`).
- `examples/internet/` — DNS, PKI, botnet, Tor, IPFS, CDN, traffic, internet map, hybrid.
- `examples/blockchain/`, `examples/scion/`, `examples/yesterday_once_more/`.

## Workflow

### 1. Pick the layers
Instantiate one object per layer you need:
```python
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.core   import Emulator, Binding, Filter
from seedemu.compiler import Docker

emu  = Emulator()
base = Base(); routing = Routing(); ebgp = Ebgp(); ibgp = Ibgp(); ospf = Ospf()
```
Add a service layer object for each service (see the `seedemu-add-service` skill and
`seedemu/services/__init__.py` for what's available).

### 2. Build the Base Layer (structure only)
ASes, IXes, networks, routers, hosts — no routing logic, no app state (P2).
```python
base.createInternetExchange(100)
base.createInternetExchange(101)

as150 = base.createAutonomousSystem(150)          # transit AS
as150.createNetwork('net0')
as150.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as150.createRouter('r2').joinNetwork('net0').joinNetwork('ix101')

as151 = base.createAutonomousSystem(151)          # stub AS
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as151.createHost('web').joinNetwork('net0')
```
A router connected to an IX is automatically a BGP router. Internal routers run OSPF by default.

### 3. Express routing/peering intent (control plane)
Declare *relationships*, not raw daemon config (P7).
```python
# Provider–customer: AS150 is the provider of AS151 at IX-100
ebgp.addPrivatePeerings(100, [150], [151], PeerRelationship.Provider)
# Or peer everyone at an IX through its route server:
ebgp.addRsPeers(100, [150, 151])
```
Relationships: `PeerRelationship.Provider`, `PeerRelationship.Peer`, `PeerRelationship.Unfiltered`.

### 4. Install services on virtual nodes, then bind (P4)
Services target symbolic names; a `Binding` resolves each to a physical node at render. **Never
hard-code IPs or physical nodes inside service usage.**
```python
from seedemu.services import WebService
web = WebService()
web.install('web151')                              # 'web151' is a virtual node
emu.addBinding(Binding('web151', filter=Filter(asn=151, nodeName='web')))
```
For packaged infrastructures (e.g. DNS), use a `Component` and bind its virtual nodes
(`Action.FIRST/RANDOM/LAST/NEW` + `Filter`). See `examples/internet/B01_dns_component`.

### 5. Add layers and render
Rendering merges layers and resolves bindings into the intermediate representation.
```python
emu.addLayer(base); emu.addLayer(routing); emu.addLayer(ebgp)
emu.addLayer(ibgp); emu.addLayer(ospf); emu.addLayer(web)
emu.render()
```

### 6. Compile to a backend (the only execution-dependent step, P1)
```python
emu.compile(Docker(), './output')                  # single host
# Swap the compiler for distributed/cloud without changing steps 1–5:
# from seedemu.compiler import DistributedDocker
# emu.compile(DistributedDocker(), './output')
```

### 7. Verify
- Confirm `./output` contains `docker-compose.yml` and per-node folders.
- `cd output && docker compose build && docker compose up` (note: large topologies are
  resource-bound; see P9 on kernel limits before scaling up).
- Inspect with InternetMap (`tools/InternetMap2/`) and shell into containers; check routing with
  `birdc show route` / reachability with `ping`/`traceroute`.
- For large or distributed scenarios, prefer the distributed compiler and shard across kernels
  rather than piling containers on one host (P9).

## Checklist (maps to principles)

- [ ] Composition never references the execution backend; only `emu.compile(...)` picks it. *(P1)*
- [ ] Each concern is in the right layer; nothing pokes another layer's internals. *(P2)*
- [ ] Topology is parameterized where it should scale (loops, not copy-paste). *(P3)*
- [ ] Every service is installed on a virtual node and resolved via `Binding`/`Filter`; **zero**
      hard-coded IPs/ASNs/physical nodes. *(P4)*
- [ ] Routing is expressed as relationships, not hand-written config. *(P7)*
- [ ] The scenario lives as a runnable example with a README and expected output. *(P10)*

## Common pitfalls

- Forgetting to `addLayer` a layer you used → it won't render.
- Binding a virtual node with a `Filter` that matches nothing → resolution fails at render.
- Hard-coding an IP into service config instead of using a virtual node → breaks portability
  (the most common architecture violation).
- Assuming a 10K-node scenario runs on a laptop → respect host/kernel limits (P9).
