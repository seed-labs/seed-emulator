# SEED-Emulator Design Principles

> The canonical design philosophy of SEED-Emulator (the `seedemu` library), distilled from
> the project's design paper (`paper.pdf`, where the system is referred to anonymously as
> "SEEDX") and verified against the codebase.
>
> **If you are an AI agent developing on SEED-Emulator, read this file first.** Every change
> you make — a new service, a new layer, a new compiler, a new example — must stay faithful to
> these principles. They are the difference between extending the emulator and fighting it.

## How to read this document

Each principle is stated, justified from the design rationale, anchored to real code so the
claim stays traceable, and turned into concrete Do / Don't rules for development. The final
section, [Rules for AI Development](#rules-for-ai-development), is a compact checklist you can
load on its own before writing code.

Code paths are relative to the repository root (the directory that holds `seedemu/`,
`examples/`, and `tools/`).

---

## The one-sentence philosophy

SEED-Emulator builds **high-fidelity emulations of the Internet** by letting users **compose**
an execution-agnostic description of a network — programmatically, in layers, out of
production-grade building blocks — and then **compile** that single description down to a
concrete execution environment (Docker, distributed Docker, and beyond). Fidelity comes from
running real software on a real topology; extensibility comes from strict separation of
concerns; scale is treated as a real, kernel-bounded engineering problem.

The four design goals everything serves: **fidelity, scalability, extensibility, usability**
(for both researchers and educators).

---

## Principle 1 — Decouple composition from execution

**Statement.** The logical definition of an emulation (topology, routing, services,
configuration) is completely independent of the technology used to run it. Composition is
**execution-agnostic**; only a small, well-isolated component — the *compiler* — knows about
the execution environment.

**Why.** A research experiment should be written once and run anywhere. This separation of
concerns is what gives the emulator its longevity and extensibility: extending Docker-based
emulation to a new execution backend "only requires a new compiler" without touching any
scenario code. The paper reports the Kubernetes compiler took under a month to add precisely
because nothing above it had to change.

**In the code.**
- `seedemu/core/Compiler.py` — the `Compiler` base class. `_doCompile(emulator)` is the only
  method a backend must implement; it "takes the rendered result and compiles them to working
  emulators."
- `seedemu/compiler/Docker.py`, `DistributedDocker.py`, `GcpDistributedDocker.py` — concrete
  compilers. The same composed `Emulator` object is handed to whichever one you pick.
- Scenario code ends with `emu.compile(Docker(), './output')` — the compiler is a parameter,
  not baked into the scenario (see `examples/basic/A01_transit_as`).

**Rules for AI development.**
- ✅ Keep all execution-specific logic (image names, compose/manifest generation, volume
  mounts, scheduling) inside a compiler under `seedemu/compiler/`.
- ✅ To support a new runtime, add a new `Compiler` subclass. Do not branch on runtime inside
  layers or services.
- ❌ Never make a layer or service ask "am I running under Docker?" Composition must not know
  how it will be executed.
- ❌ Never hardcode an output path, container name, or host detail into a service's logic.

> Note: this branch ships Docker, DistributedDocker, and GCP-distributed compilers. The
> Kubernetes compiler described in the paper is the canonical example of "add a compiler, not a
> rewrite" — if/when it lands in this tree, it must follow exactly this contract.

---

## Principle 2 — Compose in layers (the Photoshop model)

**Statement.** An emulation is built as a stack of independent **layers**, much like a layered
image in Photoshop. The physical/link topology, the control-plane routing, and the
application-plane services are separate layers that can be edited, exported, and reused
independently, then **merged** into one intermediate representation at *render* time.

**Why.** Large-scale Internet emulation is too complex to build monolithically. Layering lets a
researcher swap the entire control plane (e.g. replace BGP routing with SCION) on top of the
*same* base topology to run comparative studies, without reconstructing the experiment. It is
the structural basis of the emulator's extensibility.

**The three layer categories.**
1. **Base Layer (infrastructure topology)** — the "bare metal and cabling": ASes, IXPs, networks,
   routers, hosts. No routing logic or application state. (`seedemu/layers/Base.py`)
2. **Routing Layers (control plane)** — BGP (eBGP/iBGP), OSPF, etc., overlaid on the base.
   (`seedemu/layers/{Routing,Ebgp,Ibgp,Ospf,Mpls}.py`)
3. **Service Layers (application plane)** — DNS, blockchain, CDN, Tor, PKI, … as pluggable
   modules. (`seedemu/services/`)

**In the code.**
- `seedemu/core/Layer.py` — the `Layer` interface; every layer is `Mergeable` and declares
  `addDependency(...)` so the render order is correct.
- `seedemu/core/Emulator.py` — holds the `LayerDatabase`; `render()` merges layers into the
  intermediate representation.
- A typical scenario instantiates one object per layer: `base = Base(); routing = Routing();
  ebgp = Ebgp(); ospf = Ospf()` (see `examples/basic/A01_transit_as`).

**Rules for AI development.**
- ✅ Put new functionality in the layer it belongs to: structure → Base, control plane →
  a routing layer, application → a service layer.
- ✅ Declare dependencies explicitly via `addDependency` so rendering stays ordered; don't rely
  on call order in the user's script.
- ❌ Don't reach across layers to mutate another layer's internals. Layers communicate through
  the shared `Emulator`/`Registry`, not by poking each other.
- ❌ Don't collapse concerns (e.g. a service that also rewrites routing) — split it.

---

## Principle 3 — Compose programmatically, in Python

**Statement.** Emulations are composed using a Python SDK of object-oriented building blocks,
**not** a GUI and **not** a declarative markup (YAML/XML). The composition is ordinary Python
code.

**Why.** The paper compares three approaches — GUI, declarative, and programming — and chooses
programming for **expressivity and scale**. Generating 1,000 nodes with incrementally varying
BGP configuration is a `for` loop in Python but a nightmare in a GUI or static XML. A
programming language gives dynamic topology generation, conditional logic, and parameterized
scaling for free.

**The unexpected dividend: AI-friendliness.** Because emulations are standard Python with
well-structured APIs — not opaque GUI files or rigid markup — LLMs can read, reason about, and
generate complex network configurations directly. This is *why* an AI-agent toolkit for this
project (the one you are reading) is even tractable. Preserving this property is itself a design
goal.

**In the code.**
- The SDK building blocks: `seedemu/core/` (Emulator, Node, Network, AutonomousSystem,
  InternetExchange, …), `seedemu/layers/`, `seedemu/services/`.
- Fluent, chainable APIs designed for human and LLM readability:
  `as150.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')`
  (see `examples/basic/A01_transit_as`).

**Rules for AI development.**
- ✅ Expose new capability as clean Python APIs with readable names and chainable calls where it
  fits the existing style.
- ✅ Make APIs *parameterizable* (counts, ranges, policies) so users can scale with loops.
- ✅ Keep APIs LLM-legible: explicit method names, docstrings, no magic.
- ❌ Don't introduce a YAML/GUI configuration layer as the primary interface. Generated config
  files are an *output* of compilation, never the way a user composes.

---

## Principle 4 — Virtual nodes and late binding

**Statement.** Service-layer applications are not wired directly to physical nodes or IP
addresses. Each service instance is assigned a symbolic string identifier — a **virtual node**.
At *render* time, a **binding** process resolves each virtual node onto a concrete physical
node created by the Base Layer.

**Why.** This is what makes service layers **portable**. The analogy in the paper: the base
layer is a motherboard, and service-layer applications are modular IC chips; virtual nodes are
the chip's pins. Migrating a complex DNS infrastructure to a different topology requires *zero*
reconfiguration of the DNS software — the user just changes the pin bindings. Without late
binding, every service would hard-code infrastructural dependencies and could not be reused.

**In the code.**
- `seedemu/core/Service.py` — `Server`/`Service`: services `install(...)` onto virtual nodes by
  name.
- `seedemu/core/Binding.py` — `Binding(source, action, filter)` with `Action.{RANDOM, FIRST,
  LAST, NEW}` and a `Filter` (e.g. by ASN or node name).
- `seedemu/core/Emulator.py` — `addBinding(...)`; the `BindingDatabase` resolves virtual nodes
  to physical nodes during `render()`.
- Pattern: `web.install('web151')` then `emu.addBinding(Binding('web151', filter=Filter(asn=151,
  nodeName='web')))` (see `examples/basic/A01_transit_as`). For components, e.g.
  `Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST)`.

**Rules for AI development.**
- ✅ A new service must operate on virtual node names; let the user (or a `Binding`) decide
  where it physically lands.
- ✅ Support resolution via `Filter` + `Action` rather than requiring exact node identity.
- ❌ **Never** hard-code IP addresses, ASNs, or specific physical nodes inside a service's
  logic. That breaks portability and is the single most common way to violate the architecture.
- ❌ Don't resolve bindings yourself before render — virtual nodes only become physical during
  rendering.

---

## Principle 5 — Run production-grade software, not abstract models

**Statement.** The emulator runs real, off-the-shelf software inside lightweight containers —
the BIRD routing daemon, real Ethereum clients (`geth`), Tor, real DNS servers — rather than
simplified protocol models.

**Why.** Native compatibility with production software means the same tools and workflows used
in real deployments work inside the emulator unchanged: MetaMask against the emulated
blockchain, a Beaconchain explorer against emulated Ethereum, standard `birdc`/`ping`/`iperf3`
against the network. This is the source of the emulator's **fidelity**. The deliberate trade-off
(see Principle 9 / Limitations): SEED-Emulator targets *conceptual* realism of the Internet as a
system — a lightweight container that behaves like a real router — and does **not** try to
replicate vendor hardware (ASIC micro-bursting, NIC-offload jitter). That sacrifice is what
makes large scale possible.

**In the code.**
- Routing is backed by BIRD (`seedemu/layers/Routing.py` generates real BIRD config).
- `seedemu/services/EthereumService/` runs real clients; `MoneroService`, `TorService`,
  `KuboService` (IPFS), `CDNService`, `CAService` (PKI) wrap real software.

**Rules for AI development.**
- ✅ When adding a service, integrate the *actual* upstream software and generate its real
  configuration files.
- ✅ Pin and document the software version you target (the paper pins BIRD v2.17.2, etc.).
- ❌ Don't write a fake/stub protocol when a real implementation can run in a container.
- ❌ Don't assume hardware-level timing fidelity; that is explicitly out of scope.

---

## Principle 6 — Services are self-contained, pluggable modules

**Statement.** Each service is an independent module that exposes a **high-level API** for the
user and internally translates that intent into concrete, software-specific configuration
artifacts and command-line parameters. New services plug into the ecosystem without changing
the core.

**Why.** This abstraction shields researchers from the dense, error-prone boilerplate of
manually orchestrating distributed software across hundreds of nodes. It also makes the
ecosystem **composable**: the more self-contained services exist, the easier every future
experiment becomes. The paper notes the service ecosystem (DNS/DNSSEC, Ethereum/Monero/Chainlink,
IPFS, PKI, Botnet, CDN, Tor) is a key feature most emulators lack out of the box.

**In the code.**
- `seedemu/core/Service.py` — the `Service`/`Server` contract: `install(node)` plus
  configuration setters.
- `seedemu/services/__init__.py` — the registry of exported services; a new service is wired in
  here.
- Low-level node APIs services build on: `host.addSoftware(...)`, `host.importFile(...)`,
  `host.addBuildCommand(...)`, `host.appendStartCommand(...)` — covering software install,
  configuration, and execution (paper Appendix A.4).

**Rules for AI development.**
- ✅ Model a new application as a `Service`/`Server` pair with a clean high-level API; hide the
  config boilerplate.
- ✅ Register it in `seedemu/services/__init__.py`, add an `examples/` entry, and document it.
- ✅ Reuse the node-level install/build/run APIs rather than inventing new plumbing.
- ❌ Don't require users to hand-write the service's config files — generating them *is* the
  service's job.
- ❌ Don't make a service depend on another service's internals; depend on capabilities, declared
  through the layer/dependency mechanism.

---

## Principle 7 — The routing layer is a configuration compiler with hooks

**Statement.** The Routing Layer does not ask users to write router configs. It **parses the
Base Layer abstractions** (ASes, subnets, links, peering relationships) and **automatically
generates** the protocol-specific configuration for the routing daemon — establishing eBGP
across inter-domain links, iBGP (full-mesh or route-reflector) within an AS, OSPF areas, and
baseline prefix advertisement. It also **exposes programmable hooks** so researchers can inject
custom policy (route hijacking, path prepending, traffic engineering) without rewriting the
whole config.

**Why.** Manually configuring routing tables and neighbor relationships at scale is error-prone
and kills scalability. Automating the boilerplate while keeping policy programmable is what lets
the same topology support both "just make it converge" and precise control-plane experiments.

**In the code.**
- `seedemu/layers/Routing.py` — turns topology into BIRD configuration.
- `seedemu/layers/Ebgp.py` — `addPrivatePeerings(ix, [provider], [customers], PeerRelationship.Provider)`,
  `addRsPeers(ix, [...])`, and `PeerRelationship.{Provider, Peer, Unfiltered}`. Business
  relationships are encoded with BGP Large Communities (paper Appendix A.3).
- `seedemu/layers/{Ibgp,Ospf}.py` — intra-AS control plane.
- `seedemu/components/BgpAttackerComponent.py` — an example of using the hooks to inject a
  hijack policy.

**Rules for AI development.**
- ✅ Derive routing state from Base Layer abstractions; let users express *intent* (who peers
  with whom, as what relationship), not raw config.
- ✅ Add new policy capability as a hook/filter on top of the generated config, preserving the
  automated baseline.
- ✅ Keep the design software-agnostic in spirit; the paper anticipates pluggable backends
  (FRRouting, GoBGP) alongside BIRD.
- ❌ Don't ask the user to supply daemon config text as the primary interface.

---

## Principle 8 — Fidelity is rooted in real-world data

**Statement.** Beyond synthetic topologies, SEED-Emulator constructs emulated networks **from
empirical Internet measurement data** (CAIDA AS-relationship datasets), and when the full graph
is too large, reduces it with a **BGP-semantics-preserving** sampling algorithm (SGIM) rather
than naive graph sampling.

**Why.** Structural realism is the foundation of fidelity. Real inter-domain routing is governed
by commercial policy (valley-free routing): two ASes physically attached to the same IXP cannot
exchange traffic unless a logical peering relationship exists. A topology reduction that ignores
this destroys routing semantics. SGIM reformulates reduction as influence-maximization over
routing propagation and keeps AS-internal integrity intact, so the sampled subgraph preserves
eBGP sessions and k-core structure far better than random/random-walk/community baselines.

**In the code / data path.**
- Topology generators live under `seedemu/generators/` and the real-world topology tooling;
  examples that consume real-world data: `examples/basic/A03_real_world`, real-world router
  creation `createRealWorldRouter(...)` (paper Appendix A.5).
- See `knowledge/capability-map.md` for the current set of importers/generators in this tree.

**Rules for AI development.**
- ✅ When a scenario needs realism, prefer importing real topology/relationship data over
  hand-built graphs.
- ✅ Any topology-reduction or sampling must preserve BGP business relationships and AS-internal
  integrity — never sample so that valley-free routing semantics break.
- ❌ Don't treat the Internet graph as a plain undirected graph; physical connectivity ≠ routing
  reachability.

---

## Principle 9 — Scale is a first-class, kernel-bounded engineering concern

**Statement.** Large-scale emulation is not "the same thing, but bigger." At thousands of
containerized routers on one host, the binding constraint is the **Linux kernel** — most acutely
contention on the global Routing Netlink (`rtnl_lock`) during mass route installation, which can
trigger a self-reinforcing "Netlink storm" that prevents convergence. SEED-Emulator treats this
as a real systems problem with explicit mitigations.

**Why.** The paper measures the gap directly: at 3,000 nodes the control plane converges in
~500s but the data plane takes >13,000s, dominated by RTNL contention. The mitigations:
- **Deferred kernel updates** — separate control-plane convergence from data-plane FIB
  installation, then install asynchronously at a controlled rate, with **jittering** to break
  synchronized bursts (drops average RTNL lock wait from ~150,000µs to ~685µs at 3K nodes).
- **Multi-VM deployment** — shard the RTNL synchronization domain across multiple kernels
  (≈1,000 containers per kernel keeps it below saturation), orchestrated by the Kubernetes
  compiler. This trades virtualization overhead for orders-of-magnitude faster convergence at
  scale. With these, a single 384-thread / 1 TB server reaches 10K+ routing nodes.

**In the code.**
- `seedemu/compiler/DistributedDocker.py` and the distributed/cloud compilers are where
  scale-out execution lives.
- `examples/internet/B50_bring_your_own_internet` and distributed examples show multi-host
  deployment.

**Rules for AI development.**
- ✅ When designing for scale, respect the single-kernel ceiling; prefer sharding across kernels
  (multiple VMs/hosts) over piling more containers on one kernel.
- ✅ Keep control-plane and data-plane convergence conceptually separate; for control-plane-only
  studies, converging the control plane is a valid fast path.
- ✅ Quantify scale claims against host resources (cores, RAM) and kernel limits, not just node
  counts.
- ❌ Don't assume linear scaling. Don't weaken kernel networking correctness to chase speed.

---

## Principle 10 — Reproducibility, portability, and shareability

**Statement.** The whole architecture exists so experiments are **write-once, deploy-anywhere**,
**repeatable**, and **shareable** as composable artifacts. A layer, a service, or a whole
scenario can be exported and recombined to build complex multi-domain experiments.

**Why.** This is the payoff of Principles 1–4. Decoupling + layering + programmatic composition +
late binding together let teams "seamlessly share and combine modular artifacts." It is also why
the platform doubles as an education tool (SEED Labs): small scenarios run on a 2-core / 4–8 GB
VM, large ones scale to a cluster, from the same source.

**In the code.**
- `examples/` — every capability ships as a runnable, documented example; these *are* the shared
  artifacts and the templates for new work.
- `seedemu/core/Component.py` — `Component` packages a reusable sub-emulation (e.g. a DNS
  infrastructure) exposing its virtual nodes for binding.
- The intermediate representation produced by `render()` is technology-neutral and serializable.

**Rules for AI development.**
- ✅ Ship every new capability with a runnable `examples/` entry and a README, matching existing
  conventions.
- ✅ Package reusable sub-topologies as `Component`s that expose virtual nodes.
- ✅ Make scenarios deterministic and re-runnable; document expected outputs.
- ❌ Don't build one-off code that can't be re-run or shared. If it's worth doing, it's worth
  being an artifact.

---

## Interaction & observability (supporting principle)

Once running, an emulation is meant to be **inspected and steered**: manually via container
CLIs, programmatically via the interaction library, and visually via **InternetMap**
(`tools/InternetMap2/`), which shows topology, node info, and live packet flows and lets users
control the emulator (enter containers, toggle BGP sessions). The data plane is steerable at
runtime with Linux `tc` (latency, jitter, loss, bandwidth) for "what-if" experiments. When you
add a capability, consider how it will be observed and controlled — emit metadata the
visualization can use, and make runtime state accessible.

---

## Anti-patterns (quick reference)

These directly contradict the principles above. If you find yourself doing one of these, stop:

- Hard-coding IPs/ASNs/physical nodes inside a service → violates **P4** (use virtual nodes +
  binding).
- Branching on the execution backend inside a layer/service → violates **P1** (put it in a
  compiler).
- Adding a YAML/GUI as the primary way to compose → violates **P3**.
- Stubbing a protocol instead of running the real software → violates **P5**.
- A service that also rewrites routing, or a layer that pokes another layer's internals →
  violates **P2/P6**.
- Sampling a topology in a way that breaks valley-free/BGP relationships → violates **P8**.
- Piling more containers on one kernel to "scale" → violates **P9**.
- One-off code with no example, README, or repeatability → violates **P10**.

---

## Rules for AI Development (load-this-alone checklist)

Before writing or accepting code for SEED-Emulator, confirm:

1. **Execution-agnostic.** Does composition stay independent of how it runs? Backend-specific
   logic lives only in a `Compiler`. *(P1)*
2. **Right layer.** Is the change in the correct layer — Base (structure), Routing (control
   plane), or Service (application)? Are cross-layer dependencies declared, not assumed? *(P2)*
3. **Pythonic & parameterizable.** Clean, chainable, LLM-legible API that scales with loops; no
   GUI/markup as the primary interface. *(P3)*
4. **Virtual nodes only.** Services operate on symbolic names resolved by `Binding`/`Filter`;
   **zero** hard-coded IPs/ASNs/physical nodes. *(P4)*
5. **Real software.** Integrate and configure actual upstream software; pin the version; no
   stubs. Don't claim hardware-level fidelity. *(P5)*
6. **Self-contained module.** New capability = a pluggable `Service`/`Layer`/`Component` with a
   high-level API that hides config boilerplate; registered and exported. *(P6)*
7. **Generate routing, expose hooks.** Derive routing from topology intent; add policy as
   hooks, not hand-written daemon config. *(P7)*
8. **Real data, real semantics.** Prefer empirical topology data; never break BGP business
   relationships when sampling. *(P8)*
9. **Scale honestly.** Respect kernel limits; shard across kernels; separate control-/data-plane
   convergence; quantify against resources. *(P9)*
10. **Ship an artifact.** Add a runnable `examples/` entry + README + expected outputs; make it
    reusable and repeatable. *(P10)*
11. **Observable.** Provide metadata/runtime access for InternetMap and `tc`-style inspection.

When a request would require breaking one of these, say so and propose an in-architecture
alternative rather than working against the design.

---

## See also

- `knowledge/architecture.md` — the four-phase lifecycle and layer stack with code anchors.
- `knowledge/capability-map.md` — what seedemu can do today, with evidence paths.
- `knowledge/glossary.md` — definitions of the core terms used here.
- `skills/seedemu-compose-scenario/` — how to build a new emulation scenario on these principles.
- `skills/seedemu-add-service/` — how to add a new service/layer the right way.
- `paper.pdf` — the full design paper this document distills.
