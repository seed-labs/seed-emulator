# Mini Internet With MPLS Transit AS

This example is based on `examples/internet/B00_mini_internet`. It keeps the
same Internet exchanges, transit ASes, stub ASes, route-server peerings, private
peerings, and customized AS154 host, but changes one large transit AS:

```text
AS2 uses MPLS.
AS3, AS4, AS11, AS12, and all stub ASes keep the normal B00 routing behavior.
```

AS2 is a good demonstration target because it is a tier-1 transit AS connected
to `IX100`, `IX101`, `IX102`, and `IX105`. Its IX presence and peerings are
copied from B00. Its internal links are changed to pass through non-edge core
routers, so the MPLS layer has an internal provider backbone to configure.

## Host System Support

MPLS requires support from the Linux kernel on the emulator host. Before running
the Docker runtime, load the MPLS kernel module as root:

```sh
modprobe mpls_router
```

Depending on the host distribution, `mpls_iptunnel` and `mpls_gso` may also be
needed.

## Implementation

The key difference from B00 is the AS-level MPLS core-forwarding intent:

```python
mpls = Mpls()
as2.setCoreForwarding("mpls")
```

The emulator then adds `mpls` along with the usual routing layers:

```python
emu.addLayer(base)
emu.addLayer(Routing())
emu.addLayer(ebgp)
emu.addLayer(mpls)
emu.addLayer(Ibgp())
emu.addLayer(Ospf())
```

The MPLS layer reads AS2's core-forwarding intent, masks AS2 from the regular
`Ibgp` and `Ospf` layers, and installs MPLS/LDP/OSPF configuration on AS2's
FRR border and core routers. Other ASes continue to use the normal B00
behavior.

## Standard Arguments

The example accepts both the legacy platform argument and the newer named
arguments:

```sh
python examples/internet/B31_mini_internet_mpls/mini_internet_mpls.py amd
python examples/internet/B31_mini_internet_mpls/mini_internet_mpls.py --platform amd --output examples/internet/B31_mini_internet_mpls/output
python examples/internet/B31_mini_internet_mpls/mini_internet_mpls.py --dumpfile examples/internet/B31_mini_internet_mpls/base_internet_mpls.bin
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

This example includes an `example.yaml` manifest for `seedemu.testing`. Run
these commands from the repository root:

```sh
python seedemu/testing/cli.py clean examples/internet/B31_mini_internet_mpls/example.yaml
python seedemu/testing/cli.py compile examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
python seedemu/testing/cli.py build examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
python seedemu/testing/cli.py up examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
python seedemu/testing/cli.py probe examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
python seedemu/testing/cli.py test examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
python seedemu/testing/cli.py down examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/internet/B31_mini_internet_mpls/example.yaml --artifact-dir ci-artifacts/b31
```

The readiness stage checks representative AS2 MPLS border/core routers,
unchanged non-MPLS transit routers, and stub hosts. The probe stage checks that
reachability still works across the mini Internet. The custom `test_runtime.py`
program additionally checks that AS2 routers have MPLS/LDP configuration on the
expected internal links and that an AS3 router does not have MPLS configuration.
