# A14 BGP Event Looking Glass

`A14` combines two control-plane views:

- route-table looking glass with `BgpLookingGlassService`
- event-oriented monitoring with `ExaBgpService`

## What it proves

- A classic route-table looking glass can coexist with a live event stream.
- Operators can compare stable route state with live BGP updates in one lab.
- The event dashboard is lightweight enough to be packaged as a standard SEED example.

## Topology

- `AS2/router0` is the BIRD router observed by Classic Looking Glass
- `AS2/looking-glass` hosts the Classic Looking Glass frontend
- `AS151/router0` is a BIRD peer at `ix100`
- `AS151/event-viewer` runs ExaBGP event collection and dashboard

## Build

```bash
cd examples/basic/A14_bgp_event_looking_glass
PYTHONPATH=../.. python3 bgp_event_looking_glass.py
cd output
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 COMPOSE_PROJECT_NAME=a14 docker-compose build
COMPOSE_PROJECT_NAME=a14 docker-compose up -d
```

## Runtime checks

```bash
LG=$(docker ps --format '{{.Names}}' | grep 'as2.*looking-glass')
EVT=$(docker ps --format '{{.Names}}' | grep 'as151.*ExaBGP')
R2=$(docker ps --format '{{.Names}}' | grep 'as2.*router0')
R151=$(docker ps --format '{{.Names}}' | grep 'as151.*router0')
docker exec "$LG" sh -lc 'ps aux | grep -E "seed-lg|frontend.py" | grep -v grep'
docker exec "$R2" birdc show protocols
docker exec "$R2" birdc show route all
docker exec "$EVT" sh -lc 'ps aux | grep -E "exabgp|dashboard|live_control" | grep -v grep'
docker exec "$EVT" sh -lc 'tail -n 50 /var/log/exabgp/events.jsonl; tail -n 50 /var/log/exabgp/exabgp.log'
docker exec "$EVT" sh -lc "printf '%s\n' 'announce route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
docker exec "$R151" birdc show route for 203.2.4.1 all
curl --noproxy '*' http://127.0.0.1:5003/api/events
docker exec "$EVT" sh -lc "printf '%s\n' 'withdraw route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
curl --noproxy '*' http://127.0.0.1:5002/
curl --noproxy '*' http://127.0.0.1:5003/
```

Use `http://localhost:5002/` for route-state and `http://localhost:5003/`
for the ExaBGP event stream.
