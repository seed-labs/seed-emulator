# Mini Internet With ExaBGP Speaker

This example is based on `examples/internet/B00_mini_internet`. It keeps the
same mini-Internet topology and adds one external BGP control-plane speaker:

```text
AS180/exabgp joins IX100 at 10.100.0.180.
AS180 peers with AS2/r100 at 10.100.0.2.
AS180 announces 198.51.100.0/24.
```

The purpose is to show how the `ExaBgpService` from
`examples/basic/A13_exabgp` can be attached to a larger Internet emulator. AS2
continues to use the normal mini-Internet routing stack; ExaBGP is an external
BGP speaker that injects selected routes into AS2.

## Implementation

The example first builds the B00 mini Internet:

```python
emu = mini_internet.build_emulator(hosts_per_as=hosts_per_as)
```

It then adds AS180 on IX100 and installs the ExaBGP service:

```python
as180 = base.createAutonomousSystem(180)
as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")

exabgp_speaker = exabgp.install("as180_exabgp").setLocalAsn(180)
# Prefer IX-based peering: the service resolves AS2's IX100 border router automatically.
exabgp_speaker.addPeer(ix=100, peer_asn=2, router_relationship="customer")
# Use router-based peering when multiple AS2 routers share IX100 and one must be selected explicitly.
# exabgp_speaker.addPeerByRouter("r100", router_asn=2, router_relationship="customer")
exabgp_speaker.addAnnouncement("198.51.100.0/24")
```

The active `addPeer()` call is the preferred form for the mini Internet because
it describes the BGP relationship at the IX level: AS180 peers with AS2 at
IX100. The service resolves the router automatically; in this topology, that
router is `AS2/r100`. The commented `addPeerByRouter()` form is the escape hatch
for topologies where the target AS has multiple routers on the same IX.

## Manual BGP Updates

The ExaBGP service creates a manual control FIFO inside the ExaBGP container:

```text
/run/exabgp/manual.in
```

After the emulator is running, send live BGP updates with:

```sh
sh ./exabgpctl.sh announce 203.0.113.0/24 self
sh ./exabgpctl.sh withdraw 203.0.113.0/24 self
```

You can also send raw ExaBGP commands:

```sh
sh ./exabgpctl.sh command "announce route 203.0.113.0/24 next-hop self"
```

To inspect ExaBGP logs:

```sh
sh ./exabgpctl.sh log
```

## Standard Arguments

```sh
python examples/internet/B32_mini_internet_exabgp/mini_internet_exabgp.py amd
python examples/internet/B32_mini_internet_exabgp/mini_internet_exabgp.py --platform amd --output examples/internet/B32_mini_internet_exabgp/output
python examples/internet/B32_mini_internet_exabgp/mini_internet_exabgp.py --dumpfile examples/internet/B32_mini_internet_exabgp/base_internet_exabgp.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--hosts-per-as N`: number of hosts created in each stub AS.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## TestRunner Lifecycle

Run these commands from the repository root:

```sh
python seedemu/testing/cli.py clean examples/internet/B32_mini_internet_exabgp/example.yaml
python seedemu/testing/cli.py compile examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
python seedemu/testing/cli.py build examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
python seedemu/testing/cli.py up examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
python seedemu/testing/cli.py probe examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
python seedemu/testing/cli.py test examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
python seedemu/testing/cli.py down examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/internet/B32_mini_internet_exabgp/example.yaml --artifact-dir ci-artifacts/b32
```

The readiness stage checks representative B00 nodes plus the ExaBGP speaker.
The probe stage checks ExaBGP-to-AS2 reachability and one representative B00
path. The custom runtime test checks the generated BIRD peering, ExaBGP config,
manual-control FIFO, and AS2's route table for the announced prefix.
