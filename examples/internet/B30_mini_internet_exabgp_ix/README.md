# Mini Internet ExaBGP IX Control Plane

This example extends `examples.internet.B00_mini_internet` with one additional
IX-connected control-plane speaker:

- `AS180` speaker `exabgp`
- IX: `ix100`
- IX address: `10.100.0.180`
- Local ASN: `180`
- Announcement: `203.0.113.0/24`
- Extra static announcement: `203.0.114.0/24`
- eBGP peers: `AS2/r100` and `AS3/r100`

The speaker runs ExaBGP, a live control FIFO, a JSON event log, and a small
dashboard. ExaBGP is installed through `ExaBgpService` and bound to an
IX-attached AS180 host. It speaks BGP on the peering LAN and can inject or
observe routes at the exchange. It is not modeled as a normal host service
behind an AS router, and it is not a full BIRD/FRR-style transit router
backend.

The base mini-internet is generated as a control-plane topology without regular
end hosts, because this example is about IX BGP tooling rather than data-plane
web services.

## Running

Generate the Docker output:

```bash
PYTHONPATH=. python3 examples/internet/B30_mini_internet_exabgp_ix/mini_internet_exabgp_ix.py amd
```

Use `arm` instead of `amd` for ARM64 images.

The dashboard listens on container port `5000`. The host port is read from
`SEED_B30_EXABGP_PORT` and defaults to `5106`:

```bash
SEED_B30_EXABGP_PORT=5106 PYTHONPATH=. python3 examples/internet/B30_mini_internet_exabgp_ix/mini_internet_exabgp_ix.py amd
```

Start the emulation manually:

```bash
cd examples/internet/B30_mini_internet_exabgp_ix/output
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 COMPOSE_PROJECT_NAME=b30 docker-compose build
COMPOSE_PROJECT_NAME=b30 docker-compose up -d
```

After BGP converges, open the dashboard at:

```text
http://localhost:5106/
```

If you changed `SEED_B30_EXABGP_PORT`, use that host port instead.
For command-line checks on hosts with an HTTP proxy configured, bypass the proxy:

```bash
curl --noproxy '*' http://127.0.0.1:5106/
```

## Live route injection

The AS180 speaker exposes ExaBGP's native CLI pipes and SEED's
`/run/exabgp/live.in` FIFO inside the ExaBGP container. Use either path to
announce or withdraw routes without regenerating the topology or editing
`/etc/exabgp/exabgp.conf`.

```bash
EXA=$(docker ps --format '{{.Names}}' | grep 'as180.*exabgp')
R2=$(docker ps --format '{{.Names}}' | grep 'as2.*r100')
R3=$(docker ps --format '{{.Names}}' | grep 'as3.*r100')
docker exec "$EXA" sh -lc 'test -p /run/exabgp/live.in && test -p /run/exabgp.in && test -p /run/exabgp.out'
docker exec "$EXA" exabgpcli announce route 203.2.3.0/24 next-hop self
sleep 3
docker exec "$R2" birdc show route for 203.2.3.1 all
docker exec "$R3" birdc show route for 203.2.3.1 all
docker exec "$EXA" exabgpcli withdraw route 203.2.3.0/24 next-hop self
sleep 3
docker exec "$R2" birdc show route for 203.2.3.1 all
```

The SEED live FIFO uses the same ExaBGP text API and is easier to script:

```bash
docker exec "$EXA" sh -lc "printf '%s\n' 'announce route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
sleep 3
docker exec "$R2" birdc show route for 203.2.4.1 all
docker exec "$R3" birdc show route for 203.2.4.1 all
docker exec "$EXA" sh -lc "printf '%s\n' 'withdraw route 203.2.4.0/24 next-hop self' > /run/exabgp/live.in"
docker exec "$EXA" sh -lc 'tail -n 30 /var/log/exabgp/live-control.log; tail -n 30 /var/log/exabgp/events.jsonl'
curl --noproxy '*' http://127.0.0.1:5106/api/events
```

`events.jsonl` should include live-control JSON entries for FIFO ready,
announce, and withdraw commands.

## Notes

The AS180 node is an IX-connected BGP speaker service:

```python
as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")
exabgp.install("as180_exabgp").setLocalAsn(180).addPeer("r100", router_asn=2)
emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))
```

This keeps BIRD/FRR as real router backends and uses ExaBGP for control-plane
peer, announce, withdraw, observe, and event-stream workflows.
The example uses the normal B00 Docker network mode rather than self-managed
dummy-address mode, because published dashboard ports must remain reachable from
the host.
