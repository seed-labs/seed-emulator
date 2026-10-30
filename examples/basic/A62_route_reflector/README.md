# Route Reflector Mini Internet

This example extends the `B00_mini_internet` topology with iBGP Route Reflector
configuration. It keeps the same IX, stub AS, and eBGP peering shape, then
uses selected transit ASes to demonstrate three iBGP modes:

- `AS2`: no RR metadata, rendered as legacy full-mesh iBGP.
- `AS12`: one RR cluster with `r101` as the RR and `r104` as the client.
- `AS3`: a larger transit AS with two RR clusters. `r100` reflects for the
  west-side clients `r105`, `r110`, and `r111`; `r103` reflects for the
  east-side clients `r104`, `r112`, and `r113`. The two RRs are meshed with
  each other.

## Why Route Reflection Is Better

In a transit AS, all BGP-speaking routers need a way to share routes learned
from external peers. Without route reflectors, iBGP usually uses a full mesh:
every router peers with every other router inside the same AS. For the eight
routers in `AS3`, that design would need:

```text
8 * 7 / 2 = 28 iBGP sessions
```

This example uses route reflection instead. The same eight-router AS is
organized as two clusters:

```text
West cluster:
  r100 = route reflector
  r105, r110, r111 = clients

East cluster:
  r103 = route reflector
  r104, r112, r113 = clients

Inter-cluster:
  r100 <-> r103
```

With this design, each client only needs an iBGP session to its local route
reflector, and the route reflectors peer with each other. The control plane is
smaller and easier to manage, while BGP routes can still be distributed across
the whole AS. Readers can compare the full-mesh model in `AS2`, the minimal
one-RR model in `AS12`, and the larger two-cluster model in `AS3`.

## Files

- `route_reflector.py`: topology entrypoint. Supports the standard example
  arguments used by `seedemu/testing/cli.py`.
- `example.yaml`: test manifest for compile, build, runtime readiness, probes,
  and the custom runtime test.
- `test_runtime.py`: custom runtime validation using `ComposeRuntimeTest`.
- `output/`: generated Docker compiler output, removed by the clean command.

## Run

From the repository root:

```sh
python examples/basic/A62_route_reflector/route_reflector.py --platform amd --output examples/basic/A62_route_reflector/output
```

The legacy platform argument is also accepted:

```sh
python examples/basic/A62_route_reflector/route_reflector.py amd
```

## Test Runner

Use the standardized runner from the repository root:

```sh
python seedemu/testing/cli.py clean examples/basic/A62_route_reflector/example.yaml
python seedemu/testing/cli.py compile examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
python seedemu/testing/cli.py build examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
python seedemu/testing/cli.py up examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
python seedemu/testing/cli.py probe examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
python seedemu/testing/cli.py test examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
python seedemu/testing/cli.py down examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/basic/A62_route_reflector/example.yaml --artifact-dir ci-artifacts/a62
```

## Runtime Checks

The manifest validates simple fixed runtime checks:

- all router services and ping endpoint services used by the runtime checks are
  running;
- representative hosts can communicate across AS boundaries in both tested
  directions.

The custom `test_runtime.py` validates dynamic or example-specific behavior:

- generated routers have healthy BIRD protocols, with BGP sessions established;
- every generated router service is discovered from Docker Compose metadata,
  including both border routers (`brdnode_*`) and internal routers (`rnode_*`);
- routers in RR-enabled ASes (`AS3` and `AS12`) expose iBGP protocol names that
  contain `rr`.

The `AS3` runtime checks include all eight routers, so the test verifies both
the route reflectors and the additional internal RR clients.

## RR API Pattern

Use RR mode by registering a cluster on the AS, assigning routers to it, and
marking the RR router:

```python
as12 = base.getAutonomousSystem(12)
as12.setIbgpMode("route-reflector")
as12.createBgpCluster("10.12.0.1")
as12.getRouter("r101").joinBgpCluster("10.12.0.1").makeRouteReflector()
as12.getRouter("r104").joinBgpCluster("10.12.0.1")
```

If an AS has no RR and only the implicit default cluster, `Ibgp` keeps the
legacy full-mesh behavior.
