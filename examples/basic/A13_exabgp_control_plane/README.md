# A13 ExaBGP Control Plane

`A13` adds ExaBGP into a SEED topology as a reusable control-plane tool node.

The ExaBGP host peers with a router over the local AS network, records BGP
events, and can announce a test prefix.

## What it proves

- ExaBGP can be embedded as a first-class control-plane utility inside the emulator.
- The peer router can keep its normal eBGP role while ExaBGP acts as a scoped tool.
- The built-in dashboard exposes live ExaBGP JSON events over HTTP.

## Topology

- `AS2/router0` is the provider edge
- `AS151/router0` is the customer edge
- `AS151/control-plane-tool` runs ExaBGP and peers with `AS151/router0`

## Build

```bash
cd examples/basic/A13_exabgp_control_plane
python3 exabgp_control_plane.py
```

## Runtime checks

After `docker compose up -d` inside `output/`:

```bash
docker exec <exabgp-container> tail -n 50 /var/log/exabgp/events.jsonl
docker exec <router-container> birdc show protocols
```

The ExaBGP dashboard is available on the ExaBGP host IP at port `5000`.
