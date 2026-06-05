# A13 ExaBGP Control Plane

`A13` adds ExaBGP into a SEED topology as an IX-facing control-plane speaker.

The ExaBGP speaker joins the IX peering LAN directly, records BGP events, and
can announce or withdraw prefixes through both ExaBGP's native `exabgpcli`
named pipes and SEED's `/run/exabgp/live.in` FIFO.

## What it proves

- The current branch can install an ExaBGP speaker as a standard service with
  `ExaBgpService` and `Binding`.
- The ExaBGP node is an IX-attached BGP speaker host, not a BIRD/FRR-style
  transit router backend and not a hidden host behind another AS router.
- The peer router keeps its normal BIRD backend while ExaBGP acts as an IX BGP speaker.
- The built-in dashboard exposes ExaBGP JSON events and live-control commands over HTTP.

## Topology

- `AS2/router0` is the provider edge
- `AS180/exabgp` is an ExaBGP speaker on `ix100` at `10.100.0.180`
- `AS180/exabgp` announces `198.51.100.0/24` to `AS2/router0`

Core API shape:

```python
as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")
exabgp.install("as180_exabgp").setLocalAsn(180).addPeer("router0", router_asn=2)
emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))
```

## Build

```bash
PYTHONPATH=. python3 examples/basic/A13_exabgp_control_plane/exabgp_control_plane.py
cd examples/basic/A13_exabgp_control_plane/output
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 COMPOSE_PROJECT_NAME=a13 docker-compose build
COMPOSE_PROJECT_NAME=a13 docker-compose up -d
```

## Runtime checks

```bash
EXA=$(docker ps --format '{{.Names}}' | grep 'as180.*exabgp')
R2=$(docker ps --format '{{.Names}}' | grep 'as2.*router0')
docker exec "$EXA" sh -lc 'ps aux | grep -E "exabgp|dashboard|live_control" | grep -v grep'
docker exec "$EXA" sh -lc 'test -f /etc/exabgp/exabgp.conf && sed -n "1,180p" /etc/exabgp/exabgp.conf'
docker exec "$EXA" sh -lc 'test -p /run/exabgp/live.in && test -p /run/exabgp.in && test -p /run/exabgp.out'
docker exec "$R2" birdc show protocols
docker exec "$R2" birdc show route for 198.51.100.1 all
docker exec "$EXA" exabgpcli announce route 203.2.3.0/24 next-hop self
sleep 3
docker exec "$R2" birdc show route for 203.2.3.1 all
docker exec "$EXA" exabgpcli withdraw route 203.2.3.0/24 next-hop self
sleep 3
docker exec "$R2" birdc show route for 203.2.3.1 all
docker exec "$EXA" sh -lc "printf '%s\n' 'announce route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
sleep 3
docker exec "$R2" birdc show route for 203.2.4.1 all
docker exec "$EXA" sh -lc "printf '%s\n' 'withdraw route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
docker exec "$EXA" sh -lc 'tail -n 40 /var/log/exabgp/live-control.log; tail -n 40 /var/log/exabgp/events.jsonl'
curl --noproxy '*' http://127.0.0.1:5001/api/events
```

The ExaBGP dashboard is available at `http://localhost:5001/`.
`events.jsonl` should include live-control JSON entries for FIFO ready,
announce, and withdraw commands.
