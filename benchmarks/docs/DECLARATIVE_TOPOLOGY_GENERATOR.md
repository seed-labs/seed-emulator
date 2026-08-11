# Declarative Topology Generator

The topology layer turns a bounded JSON request into a deterministic SEED
Emulator topology. It is separate from fault-case planning: topology generation
creates audited assets and fault bindings; scenario generation consumes those
bindings without relaxing the existing mutation and verifier safety gates.

## Workflow

```text
request.json
  -> strict schema and resource budget
  -> connected AS graph
  -> deterministic ASN/LAN/IX allocation
  -> immutable plan and SHA-256 fingerprint
  -> SEED Emulator render/compile
  -> Compose asset inventory and fault-component bindings
  -> topology smoke test
```

Start from `generator/topology/examples/small_ring.json`:

```bash
cd benchmarks
python3 -m generator.topology.cli plan \
  --spec generator/topology/examples/small_ring.json
python3 -m generator.topology.cli register \
  --spec generator/topology/examples/small_ring.json
python3 -m generator.topology.cli compile --topology-id small_ring
python3 -m generator.topology.cli validate --topology-id small_ring
python3 -m generator.topology.cli bind --topology-id small_ring \
  --component bird_wrong_asn --sequence 0 --seed example
python3 -m generator.topology.cli smoke --topology-id small_ring
```

Registered inputs and plans are stored under
`benchmarks/topology_specs/<topology_id>/`. Generated Compose output is isolated
under `benchmarks/generated/declarative/<topology_id>/output/`. A registered
topology is exposed to the benchmark CLI as
`DECLARATIVE_<topology_id>`; the CLI and manager resolve its build command and
output path without adding another hard-coded mapping.

## Model

The request controls:

- AS count and hosts per AS;
- topology policy: `tree`, `ring`, `mesh`, `random_connected`, or `explicit`;
- optional extra links or exact AS-index edge pairs;
- deterministic master seed and starting ASN;
- mutually disjoint IPv4 LAN, IX, and router-loopback pools plus prefix sizes;
- AMD64/ARM64 compilation platform;
- maximum ASes, links, containers, networks, memory estimate, and CPU estimate.

Each AS receives one BIRD router, one LAN, and the requested hosts. Every
inter-AS edge receives its own IX subnet and eBGP peering. The planner rejects
disconnected explicit graphs, duplicate/self edges, exhausted address/ASN
ranges, overlapping pools, and every resource-budget overrun before rendering.
The first usable address of every LAN and IX subnet is reserved for Docker's
bridge gateway; routers and hosts are allocated only from the remaining range.
Router loopbacks are explicitly allocated from `loopback_pool` (default
`100.64.0.0/10`) so SEED's default loopback range cannot silently overlap a LAN.
The compiler marks generated Docker bridges with the `nat-unprotected` IPv4
gateway mode. Current Docker releases otherwise filter packets forwarded by a
SEED router between two bridges, even when BIRD and the Linux route table are
correct; the compiled-output validator requires this compatibility setting.

Resource estimates are admission-control bounds rather than Docker runtime
limits. The compiled-output validator additionally checks the actual Compose
service and SEED asset counts against the approved plan.
The optional SEED Internet Map is disabled: it is not required by benchmark
probes, consumes an extra container, and otherwise binds a fixed host port that
prevents independent topologies from coexisting.

## Fault reuse

`topology_manifest.json` derives assets from SEED's Compose labels rather than
guessing container names. It publishes concrete bindings for:

- `container_stopped` and `dns_nameserver` on generated hosts;
- `bird_wrong_asn` with each router's correct ASN;
- scoped ACL faults with each router's actual IX interfaces.

These bindings provide the exact containers, ASNs, addresses, and interfaces
needed by the existing fault components. Generated scenarios must still pass
the current component target-union, read-only activation check, reverse cleanup,
root-cause, and command safety validation before execution.

The `bind` command is the adapter boundary between both layers. It chooses a
deterministic compatible target from the compiled capability manifest and emits
the exact parameters expected by one of the four existing components. It does
not inject the fault, so binding can be inspected and blind-test cases can be
assembled before any mutation is authorized.

The main generator also consumes this adapter directly. For example, the
following previews four quarantined cases without writing a suite or executing
any mutation:

```bash
python3 -m generator.agent preview \
  --suite-id declarative_preview --count 4 --seed example \
  --topology DECLARATIVE_small_ring \
  --template container_stopped --template dns_nameserver \
  --template bird_wrong_asn --template random_complex_transit_acl
```

Declarative parameters are rechecked against the compiled capability manifest
inside the existing scenario validator before commands are rendered. The
normal target-union, repair-scope, command allowlist, activation-check, cleanup,
root-cause, quarantine, and blind-observation gates remain unchanged.

## Testing and limitations

The smoke command starts the topology under a topology-specific Compose project,
waits for all SEED assets, verifies end-to-end cross-AS ping, writes a JSON audit
report under `benchmarks/reports/`, and tears down only that project unless
`--keep-running` is requested.

The first implementation supports one router and one LAN per AS, IPv4 eBGP,
and at most the limits admitted by the request budget. Multi-router ASes,
IPv6-only plans, MPLS, route reflectors, and per-container Docker CPU/memory
enforcement are future topology-model extensions; they are not silently
approximated by the current compiler.

Planning tests also cover a 10,000-business-container request (50 ASes, one
router and 199 hosts per AS). This proves deterministic model and budget
handling at that size; it is deliberately not a claim that the current VM has
enough resources to compile or run all 10,000 Docker containers.
