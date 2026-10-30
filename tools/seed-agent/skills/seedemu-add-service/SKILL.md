---
name: seedemu-add-service
description: Use when extending SEED-Emulator (seedemu) with a new capability — a new application service, a new routing/protocol layer, a reusable component, or a new execution compiler. Covers the Service/Server pattern, virtual-node + late-binding design, where to register and document the addition, and a principle-aligned checklist that distinguishes light top-layer work from substantial core changes.
---

# Add a Capability to SEED-Emulator

Extend the emulator the way the architecture intends — as a pluggable module — so the addition
composes with everything else and stays faithful to the design.

## Read first

- [`../../PRINCIPLES.md`](../../PRINCIPLES.md) — especially P4 (virtual nodes + late binding),
  P5 (real software), P6 (self-contained pluggable modules), and for layers P2/P7, for compilers
  P1.
- [`../../knowledge/architecture.md`](../../knowledge/architecture.md) — core abstractions and
  the repo map.
- [`../../knowledge/capability-map.md`](../../knowledge/capability-map.md) — check whether the
  capability already exists before building it.

## Decide what you're adding

| You want to add… | Build a… | Lives in | Base class |
| --- | --- | --- | --- |
| An application (DNS, a server, a chain client, …) | **Service / Server** | `seedemu/services/` | `Service`, `Server` (`seedemu/core/Service.py`) |
| A control-plane protocol / routing behavior | **Layer** | `seedemu/layers/` | `Layer` (`seedemu/core/Layer.py`) |
| A reusable packaged sub-topology | **Component** | `seedemu/components/` | `Component` (`seedemu/core/Component.py`) |
| Support for a new execution backend | **Compiler** | `seedemu/compiler/` | `Compiler` (`seedemu/core/Compiler.py`) |

Classify the effort honestly:
- **Light top-layer development** — a new service/component built from existing node APIs, plus
  scenario/example/parser code. No core change.
- **Substantial development** — a new layer, protocol model, compiler, or a change to core
  render/compile assumptions.

## Adding a Service (the most common case)

A Service is a layer that installs Servers onto virtual nodes. The canonical small reference is
`seedemu/services/WebService.py`. Pattern:

```python
from __future__ import annotations
from seedemu.core import Node, Service, Server

class MyServer(Server):
    def __init__(self):
        super().__init__()
        self.__port = 8080                      # config with sensible defaults

    def setPort(self, port: int) -> 'MyServer': # high-level, chainable API (P3)
        self.__port = port
        return self

    def install(self, node: Node):
        """Translate intent → real software + real config on this node (P5, P6)."""
        node.addSoftware('my-real-package')                      # install real software
        node.setFile('/etc/myapp/config', f'port={self.__port}') # generate real config
        node.appendStartCommand('myapp --config /etc/myapp/config &')
        node.appendClassName('MyService')                        # metadata for visualization

class MyService(Service):
    def __init__(self):
        super().__init__()
        self.addDependency('Base', False, False)     # declare render-order deps (P2)
        self.addDependency('Routing', False, False)

    def _createServer(self) -> Server:
        return MyServer()

    def getName(self) -> str:
        return 'MyService'
```

Then use it on **virtual nodes** with late binding (P4):
```python
svc = MyService()
svc.install('myapp-1')                                  # virtual node name
emu.addBinding(Binding('myapp-1', filter=Filter(asn=150)))
```

Key node-level APIs your `install()` builds on (paper Appendix A.4):
`addSoftware`, `importFile`/`setFile`, `addBuildCommand` (run at image build),
`appendStartCommand` (run at container boot), `joinNetwork`.

### Hard rules for a Service
- ✅ Operate on virtual node names only; let `Binding`/`Filter` choose physical placement. **No
  hard-coded IPs/ASNs/physical nodes.** *(P4)*
- ✅ Integrate the **real** upstream software and generate its real config; pin the version. *(P5)*
- ✅ Hide config boilerplate behind a clean, chainable high-level API. *(P3, P6)*
- ✅ Declare dependencies (`addDependency`) so render order is correct. *(P2)*
- ✅ Emit metadata (`appendClassName`, display info) so InternetMap can show it.
- ❌ Don't reach into another service's internals; depend on capabilities via layers/deps. *(P6)*
- ❌ Don't branch on the execution backend. *(P1)*

## Adding a Layer
Subclass `Layer` (`seedemu/core/Layer.py`); implement render behavior and declare dependencies.
A control-plane layer should **derive config from Base Layer abstractions** and expose
programmable hooks rather than asking users for raw daemon config (P7). Study
`seedemu/layers/{Ebgp,Ospf}.py`. Keep it software-agnostic in spirit (the design anticipates
FRRouting/GoBGP backends beside BIRD).

## Adding a Compiler
Subclass `Compiler` (`seedemu/core/Compiler.py`) and implement `_doCompile(emulator)` +
`getName()`. The compiler is the **only** place that knows the execution technology (P1). It
consumes the rendered representation and emits backend files — it must work on any composed
emulation without requiring scenario changes. Study `seedemu/compiler/Docker.py` and
`DistributedDocker.py`. For scale-out backends, respect the kernel-sharding lessons in P9.

## Wire it in (every addition)

1. **Export it.** Add to the relevant `__init__.py` (`seedemu/services/__init__.py`,
   `layers/__init__.py`, `components/__init__.py`, or `compiler/__init__.py`).
2. **Ship an example.** Add a runnable, documented scenario under `examples/` following the
   naming/structure of its siblings, with a README and expected output. *(P10)*
3. **Document it.** Add/extend the matching page under `docs/user_manual/` (usage) and, for core
   extensions, `docs/developer_manual/`.
4. **Test it.** Add a test alongside the existing test suite; verify the example renders,
   compiles, and runs.
5. **Refresh the capability map.** Run [`../seedemu-capability-refresh`](../seedemu-capability-refresh/SKILL.md)
   and add an entry to [`../../knowledge/capability-map.md`](../../knowledge/capability-map.md)
   with category, support status, example path, evidence, and limits.

## Final checklist (maps to principles)

- [ ] Right abstraction chosen (Service / Layer / Component / Compiler).
- [ ] Virtual nodes + binding; zero hard-coded physical detail. *(P4)*
- [ ] Real software integrated and version-pinned; config generated, not hand-written. *(P5, P7)*
- [ ] Clean high-level chainable API; boilerplate hidden. *(P3, P6)*
- [ ] Dependencies declared; no cross-layer poking; no backend branching. *(P1, P2, P6)*
- [ ] Exported, exampled, documented, tested. *(P10)*
- [ ] Capability map updated.
- [ ] If security-sensitive: framed as closed-emulation only; no real-world attack enablement.
