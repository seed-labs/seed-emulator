# A13 ExaBGP

`A13` installs ExaBGP as a SEED service speaker through `ExaBgpService` and
`Binding`.

ExaBGP is not a `Routing` backend. The peer router keeps its normal BIRD or FRR
daemon, and the service records a router-facing BGP peer intent that `Routing`
renders for that router.

## What It Proves

- ExaBGP is installed on a bound host node.
- The ExaBGP node joins the IX peering LAN directly.
- `Routing` renders the peer session on the real router.
- Static IPv4 announcements are emitted from `/etc/exabgp/exabgp.conf`.

## Topology

- `AS2/router0` is a normal BIRD router on `ix100`.
- `AS180/exabgp` is a host on `ix100` at `10.100.0.180`.
- `AS180/exabgp` announces `198.51.100.0/24` to `AS2/router0`.

The ExaBGP peer is declared by IX and AS number:

```python
exabgp_speaker = exabgp.install("as180_exabgp").setLocalAsn(180)
# Prefer IX-based peering: the service resolves the AS2 router on IX100 automatically.
exabgp_speaker.addPeer(ix=100, peer_asn=2, router_relationship="customer")
# Use router-based peering when multiple AS2 routers share IX100 and one must be selected explicitly.
# exabgp_speaker.addPeerByRouter("router0", router_asn=2, router_relationship="customer")
exabgp_speaker.addAnnouncement("198.51.100.0/24")
```

The active `addPeer()` call is the preferred form for most examples. It says
that AS180 should peer with AS2 at IX100, and the service finds the AS2 router
attached to that IX. The commented `addPeerByRouter()` form is useful when the
target AS has more than one router on the same IX and the example needs to
choose a specific one.

## Manual BGP Updates

The ExaBGP service also creates a manual control FIFO inside the ExaBGP
container:

```text
/run/exabgp/manual.in
```

Use `exabgpctl.sh` from this directory to send live BGP updates after the
emulator is running:

```bash
sh ./exabgpctl.sh announce 203.0.113.0/24 self
sh ./exabgpctl.sh withdraw 203.0.113.0/24 self
```

You can also send a raw ExaBGP command:

```bash
sh ./exabgpctl.sh command "announce route 203.0.113.0/24 next-hop self"
```

To inspect ExaBGP logs:

```bash
sh ./exabgpctl.sh log
```

The script defaults to `output/docker-compose.yml` and service
`hnode_180_exabgp`. Override them if needed:

```bash
COMPOSE_FILE=/path/to/docker-compose.yml EXABGP_SERVICE=hnode_180_exabgp sh ./exabgpctl.sh announce 203.0.113.0/24 self
```

## Test Runner

```bash
python3 -m seedemu.testing.cli clean examples/basic/A13_exabgp/example.yaml
python3 -m seedemu.testing.cli compile examples/basic/A13_exabgp/example.yaml
python3 -m seedemu.testing.cli build examples/basic/A13_exabgp/example.yaml
COMPOSE_PROJECT_NAME=seedemu-a13 python3 -m seedemu.testing.cli all examples/basic/A13_exabgp/example.yaml
```

The runtime test checks `/etc/exabgp/exabgp.conf`, the ExaBGP process, IX100
reachability, the manual control FIFO, and the generated BGP peer on
`AS2/router0`.
