# A12 BGP Mixed Backend

`A12` demonstrates mixed BGP control planes inside one SEED topology.

The network keeps the default BIRD-based path on some routers and converts selected
routers to FRRouting with the new `FrrBgp` layer.

## What it proves

- BIRD and FRRouting can coexist in one emulated network.
- Selected routers can run FRR for BGP while neighboring routers still use BIRD.
- The control-plane tooling can inspect both backends in one runtime.

## Topology

- `AS2` is a transit provider with two internal routers: `r1` and `r2`
- `AS151` and `AS152` are customer ASes
- `AS2/r2` and `AS151/router0` run FRRouting for BGP
- `AS2/r1` and `AS152/router0` stay on BIRD

## Build

```bash
cd examples/basic/A12_bgp_mixed_backend
python3 bgp_mixed_backend.py
```

## Runtime checks

After `docker compose up -d` inside `output/`:

```bash
docker exec as2r2-10.2.0.?.? vtysh -c 'show bgp summary'
docker exec as151router0-10.151.0.254 vtysh -c 'show bgp summary'
docker exec as2r1-10.2.0.?.? birdc show protocols
docker exec as152router0-10.152.0.254 birdc show protocols
```

The exact container names are generated in `output/docker-compose.yml`.
