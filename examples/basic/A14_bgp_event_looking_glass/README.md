# A14 BGP Event Looking Glass

`A14` combines two control-plane views:

- route-table looking glass with `BgpLookingGlassService`
- event-oriented monitoring with `ExaBgpService`

## What it proves

- A classic route-table looking glass can coexist with a live event stream.
- Operators can compare stable route state with live BGP updates in one lab.
- The event dashboard is lightweight enough to be packaged as a standard SEED example.

## Topology

- `AS2/router0` publishes route-table visibility through the legacy looking glass service
- `AS151/event-viewer` runs ExaBGP to collect and visualize live BGP events

## Build

```bash
cd examples/basic/A14_bgp_event_looking_glass
python3 bgp_event_looking_glass.py
```

## Runtime checks

After `docker compose up -d` inside `output/`:

```bash
docker exec <lg-container> ps aux
docker exec <event-viewer-container> tail -n 50 /var/log/exabgp/events.jsonl
```

Use the container IPs from `output/docker-compose.yml`:

- `http://<looking-glass-ip>:5000` for the route-table looking glass
- `http://<event-viewer-ip>:5000` for the ExaBGP event dashboard
