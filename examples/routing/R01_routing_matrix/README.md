# R01 Routing Matrix Regression

This example is a compact regression suite for the routing control plane. It
uses several independent transit ASes in one emulator. Each transit AS
demonstrates one routing design/backend combination.

## Matrix

```text
AS2: all-router full mesh, BIRD
AS3: all-router full mesh, FRR
AS4: all-router route reflector, BIRD
AS5: all-router route reflector, FRR
AS6: auto-completed route reflector, mixed BIRD/FRR
AS7: edge-only full mesh, mixed BIRD/FRR
```

Each transit AS connects two stub ASes. For example:

```text
AS150 -- IX100 -- AS2 -- IX101 -- AS151
```

The slices are independent, so a failure usually points to one routing design.

## What This Tests

- eBGP private peering at IXes
- iBGP all-router full mesh
- iBGP route-reflector rendering
- deterministic AS-level route-reflector auto-completion
- BIRD BGP rendering
- FRR BGP rendering
- mixed BIRD/FRR iBGP interoperability
- edge-only iBGP control-plane structure

AS7 is a structural BGP-free-core control-plane test. It intentionally does not
require end-to-end plain-IP forwarding because the core routers do not carry the
external BGP table.

## Run

From the repository root:

```sh
python seedemu/testing/cli.py clean examples/routing/R01_routing_matrix/example.yaml
python seedemu/testing/cli.py compile examples/routing/R01_routing_matrix/example.yaml
python seedemu/testing/cli.py build examples/routing/R01_routing_matrix/example.yaml
python seedemu/testing/cli.py all examples/routing/R01_routing_matrix/example.yaml
```

The custom runtime test inspects generated Docker Compose labels and router
configuration files, then writes `routing-matrix-runtime-test.json` into the
test artifact directory.
