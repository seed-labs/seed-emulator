# Complex Generated Routing Regression

This example demonstrates a larger generated transit AS. It is meant to stress
the routing layers with a less hand-crafted topology while still following the
same lifecycle pattern as `examples/sample`.

The default topology creates:

- one generated transit AS, `AS10`;
- four eBGP routers connected to four IXes;
- twelve generated internal routers;
- two stub ASes per IX, producing `AS170` through `AS177`;
- a deterministic 50/50 backend split between BIRD and FRR;
- all-router full-mesh iBGP by default.

The generated topology is written to `output/topology.json` and
`output/topology.txt`, so developers, CI, and agents can inspect the exact graph
that was produced for a run.

## Files

- `complex_generated_routing.py`: standardized SEED Emulator example entrypoint.
- `example.yaml`: test manifest consumed by the runner.
- `test_runtime.py`: custom runtime checks for topology artifacts, backend mix,
  rendered BGP config, and cross-stub reachability.
- `output/`: generated Docker compiler output and topology artifacts.

## Standard Run

From the repository root:

```sh
python examples/routing/R03_complex_generated_routing/complex_generated_routing.py --platform amd --output examples/routing/R03_complex_generated_routing/output
```

The full testing lifecycle is:

```sh
python seedemu/testing/cli.py all examples/routing/R03_complex_generated_routing/example.yaml --artifact-dir ci-artifacts/r03-complex-generated-routing
```

## Routing Options

The default iBGP design is all-router full mesh:

```sh
python examples/routing/R03_complex_generated_routing/complex_generated_routing.py
```

Use route-reflector mode with one cluster:

```sh
python examples/routing/R03_complex_generated_routing/complex_generated_routing.py --ibgp-mode rr
```

Use route-reflector mode with multiple clusters:

```sh
python examples/routing/R03_complex_generated_routing/complex_generated_routing.py --ibgp-mode rr --rr-clusters 3
```

In multi-cluster RR mode, routers are assigned to deterministic balanced
clusters. The route reflector in each cluster is the highest-degree router in
that cluster. The iBGP layer then meshes the route reflectors with each other,
so routes can move between clusters.

## Topology Options

Useful knobs include:

- `--seed`: controls deterministic topology generation.
- `--internal-routers`: number of internal routers.
- `--ixes`: comma-separated IX list.
- `--stubs-per-ix`: number of stub ASes attached to each IX. The default is
  `2`.
- `--graph-model`: NetworkX graph model, such as `small_world`,
  `scale_free`, `random`, or `regular`.
- `--graph-param KEY=VALUE`: graph-model parameter. This option can be
  repeated.
- `--ebgp-attach-policy`: how generated eBGP routers attach to internal
  routers.

The number of eBGP routers is the number of IXes. Each eBGP router connects to
one IX. The example then creates `--stubs-per-ix` stub ASes on each IX and
peers each stub privately with the transit AS. Stub ASNs are allocated
deterministically from `AS170` upward.

## What The Runner Checks

The compile stage verifies that Docker output and topology artifacts are
generated.

The readiness stage checks a representative set of generated routers and all
stub hosts.

The declarative probes verify cross-stub reachability through the generated
transit AS.

The custom runtime test verifies that:

- `topology.json` exists;
- the default iBGP mode is all-router full mesh;
- the default topology creates two stub ASes per IX;
- generated routers include both BIRD and FRR;
- the backend split is balanced;
- each router renders backend-specific BGP configuration;
- selected stub ASes can reach each other through the generated AS.
