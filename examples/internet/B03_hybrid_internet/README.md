# Hybrid Internet

This example extends `B00_mini_internet` with real-world connectivity features.
The base mini Internet is built by `examples/internet/B00_mini_internet`; B03
then adds only the hybrid-specific pieces.

This keeps B00 as the single source of truth for the mini-Internet topology.
When the base topology changes, B03 inherits those changes instead of carrying
a second copy of the same IX, AS, host, and peering code.

## What B03 Adds

B03 starts with:

```python
emu = mini_internet.build_emulator(hosts_per_as=hosts_per_as)
base = emu.getLayer("Base")
ebgp = emu.getLayer("Ebgp")
```

Then it adds three hybrid features.

## Real-World AS11872

The example creates a real-world AS for Syracuse University, `AS11872`, and
connects it to `IX102`:

```python
as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter(
    "rw-11872-syr",
    prefixes=["128.230.0.0/16"],
).joinNetwork("ix102", "10.102.0.118")

ebgp.addPrivatePeerings(102, [11], [11872], PeerRelationship.Provider)
```

By default, the example uses a deterministic prefix so CI and agent-driven tests
do not depend on live Internet prefix lookup. To fetch live prefixes for
`AS11872`, use:

```sh
python examples/internet/B03_hybrid_internet/hybrid_internet.py --live-prefixes
```

## Default Real-World Gateway

The example also creates `AS99999`, a hybrid AS that routes traffic toward the
real Internet. It announces two split default prefixes:

```python
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter(
    "rw-real-world",
    prefixes=["0.0.0.0/1", "128.0.0.0/1"],
).joinNetwork("ix100", "10.100.0.99")

ebgp.addPrivatePeerings(100, [3], [99999], PeerRelationship.Provider)
```

The two prefixes cover the IPv4 address space without using `0.0.0.0/0`
directly. Packets that do not match an emulated prefix can be sent to this AS
and then forwarded to the real world through NAT.

## OpenVPN Remote Access

`AS152` is configured to allow a real-world machine to VPN into its local
network:

```python
ovpn = OpenVpnRemoteAccessProvider()
base.getAutonomousSystem(152).getNetwork("net0").enableRemoteAccess(ovpn)
```

This allows an outside host to become a participant in the emulated network.
See [the OpenVPN remote access documentation](../../../misc/openvpn-remote-access/README.md)
for client-side connection details.

## Standard Arguments

From the repository root:

```sh
python examples/internet/B03_hybrid_internet/hybrid_internet.py --platform amd --output examples/internet/B03_hybrid_internet/output
```

The legacy platform argument is also accepted:

```sh
python examples/internet/B03_hybrid_internet/hybrid_internet.py amd
```

Useful options:

```text
--platform amd|arm
--output PATH
--dumpfile PATH
--hosts-per-as N
--live-prefixes
--skip-render
--no-override
```

## Test Runner

Use the standardized runner from the repository root:

```sh
python seedemu/testing/cli.py clean examples/internet/B03_hybrid_internet/example.yaml
python seedemu/testing/cli.py compile examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
python seedemu/testing/cli.py build examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
python seedemu/testing/cli.py up examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
python seedemu/testing/cli.py probe examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
python seedemu/testing/cli.py test examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
python seedemu/testing/cli.py down examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/internet/B03_hybrid_internet/example.yaml --artifact-dir ci-artifacts/b03
```

## Runtime Checks

The declarative probes verify that normal B00 mini-Internet reachability still
works after the hybrid features are added.

The custom `test_runtime.py` validates the B03-specific additions:

- `AS11872` real-world router is generated;
- `AS11872` announces the deterministic example prefix;
- `AS99999` default real-world gateway is generated;
- `AS99999` announces the split default prefixes;
- both real-world routers have NAT setup scripts;
- an OpenVPN remote access bridge is generated for `AS152`.
