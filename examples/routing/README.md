# Routing Examples

This folder contains routing-focused regression examples. These examples are
intended to exercise control-plane combinations that are easy to break when
changing BGP, OSPF, MPLS, FRR rendering, BIRD rendering, or route-reflector
logic.

Each routing example follows the standardized `examples/sample` pattern:

- a Python entrypoint;
- an `example.yaml` test manifest;
- a `test_runtime.py` custom runtime test;
- a per-example `README.md`.

## Examples

| Example | Purpose |
| --- | --- |
| `R01_routing_matrix` | Compact routing matrix that tests BIRD, FRR, mixed backends, full-mesh iBGP, route-reflector iBGP, automatic RR completion, and structural edge-only BGP scope. It is the main CI-friendly routing control-plane regression example. |
| `R02_bgp_free_core_mpls` | Tests BGP-free-core designs where only edge routers participate in iBGP and core routers forward using MPLS/LDP. It covers edge-only full mesh and edge-only route-reflector designs, and requires host MPLS kernel support for runtime dataplane validation. |
| `R03_complex_generated_routing` | Builds a larger generated transit AS using the topology generator, mixes BIRD and FRR backends, and lets the user choose full-mesh or route-reflector iBGP. It is useful for stress-testing routing convergence and multi-cluster RR behavior. |

## Running

For a full lifecycle run:

```sh
python -m seedemu.testing.cli all examples/routing/R01_routing_matrix/example.yaml
```

Use `R01` for routine CI coverage. Use `R02` on machines with MPLS kernel
modules available. Use `R03` when you want a larger generated topology and more
stress on iBGP/OSPF convergence.
