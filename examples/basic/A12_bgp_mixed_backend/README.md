# A12 BGP Mixed Backend

`A12` demonstrates mixed BIRD and FRRouting control planes in one IPv4 SEED topology.

The default router backend remains BIRD. Only routers created with
`routingBackend="frr"` receive FRR packages, `/etc/frr/frr.conf`, and `/frr_start`.

## What It Proves

- `Router` owns the routing backend choice.
- `Ebgp`, `Ibgp`, and `Ospf` describe routing intent.
- `Routing` renders BIRD or FRR from the same intent model.
- BIRD and FRR routers can coexist without changing old default examples.

## Topology

- `AS2/r1` uses the default BIRD backend and peers at `ix100`.
- `AS2/r2` uses FRR and peers at `ix101`.
- `AS151/router0` uses FRR.
- `AS152/router0` uses the default BIRD backend.

## Test Runner

```bash
python3 -m seedemu.testing.cli clean examples/basic/A12_bgp_mixed_backend/example.yaml
python3 -m seedemu.testing.cli compile examples/basic/A12_bgp_mixed_backend/example.yaml
python3 -m seedemu.testing.cli build examples/basic/A12_bgp_mixed_backend/example.yaml
COMPOSE_PROJECT_NAME=seedemu-a12 python3 -m seedemu.testing.cli all examples/basic/A12_bgp_mixed_backend/example.yaml
```

The runtime test checks backend-specific daemons, generated config, BGP session
state, and learned route state on BIRD and FRR routers.
