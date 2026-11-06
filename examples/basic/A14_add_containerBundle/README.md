# A14: Custom ContainerBundle

This example extends `ContainerBundle` with two Debian-based services alongside
[B00's mini Internet](../../internet/B00_mini_internet/README.md). It demonstrates
explicit network pools, static attachments, shared hosts aliases, staged files,
and entrypoint wrapping. The application stays alive for inspection; it does not
run an HTTP server.

## Files

| File | Responsibility |
| --- | --- |
| [add_containerBundle.py](add_containerBundle.py) | Generate/load the topology, render it, supply bundle networks and ports, register, and compile |
| [demoContainerBundle.py](demoContainerBundle.py) | Define `DemoContainerBundle`, create its containers, and configure their services |

The example walkthrough below describes these files as currently implemented.
The [ContainerBundle design](../../../docs/designs/container_bundle.md) covers
the shared framework; [B08](../../internet/B08_internet_map_bundle/README.md)
demonstrates the concrete InternetMap bundle.

## Services and addresses

| Logical lookup key | Generated service/container name | Private bridge | Emulator attachments | Host port |
| --- | --- | --- | --- | --- |
| `demo-app` | `demo-app.demo.seed` | `172.31.0.10` | AS151/net0: `10.151.0.16`; AS152/net0: `10.152.0.16` | `8090:8080` |
| `demo-helper` | `demo-helper.demo.seed` | `172.31.0.11` | none | none |

Both services use `debian:bookworm-slim`. Their private Compose network is
`demo_bundle_network`, with subnet `172.31.0.0/24` and gateway `172.31.0.1`.
Docker Compose adds its project prefix to the actual Docker network name.

Lookup keys omit the suffix:

```python
app = demo_bundle.getContainer("demo-app")
assert app.getName() == "demo-app"
assert app.getHostname() == "demo-app.demo.seed"
```

The generated name identifies the service, container, and build directory.
`getHostname()` does not itself configure the container's OS hostname.
Port 8090 illustrates publishing a port, but there is no application listening
on container port 8080; an HTTP request to it is not a valid readiness check.

## Network and port configuration

The driver script supplies the external pool explicitly:

```python
demo_bundle.addExternalNetwork(
    network_name="demo_bundle_network",
    prefix="172.31.0.0/24",
    ip_addresses=["172.31.0.10", "172.31.0.11"],
    default_route="172.31.0.1",
)
demo_bundle.setPorts([8090])
```

The subclass iterates every external entry, attaching app at index 0 and helper
at index 1. External pool validation checks the address count, subnet membership,
duplicates, and gateway exclusion; it does not inspect existing Docker networks.

Two explicit internal entries attach only the app:

```python
demo_bundle.addInternalNetwork(
    asn="151", network_name="net0",
    ip_addresses=["10.151.0.16"], default_route="10.151.0.254",
)
demo_bundle.addInternalNetwork(
    asn="152", network_name="net0", ip_addresses=["10.152.0.16"],
)
```

The emulator is rendered first so interface-based address/router checks and
gateway lookup can run. No automatic address allocation or reservation occurs.
The second entry requests gateway lookup by omitting `default_route`. The first
nonempty gateway wins, so the app replaces its Docker default route with
`10.151.0.254` at startup. This does not force traffic to AS152 through AS151:
the directly connected AS152 subnet remains reachable through its own interface.

The subclass reads host port index 0; it does not remove it from the port list.
It requires one host port and one internal address per supplied internal entry.

## Shared hosts aliases

`DemoContainerBundle.configure()` registers the following shared records:

| Alias | Address | Meaning |
| --- | --- | --- |
| `demo-app-e.demo.seed` | `172.31.0.10` | App on the first external pool |
| `demo-helper-e.demo.seed` | `172.31.0.11` | Helper on the first external pool |
| `demo-app-demo_bundle_network` | `172.31.0.10` | App on the named bridge |
| `demo-helper-demo_bundle_network` | `172.31.0.11` | Helper on the named bridge |
| `demo-app.demo.seed` | `10.151.0.16` | App on its first internal pool |
| `demo-app-net_151_net0` | `10.151.0.16` | App on AS151/net0 |
| `demo-app-net_152_net0` | `10.152.0.16` | App on AS152/net0 |

Short external aliases are registered only for the first external pool, and the
app's generated name only for the first internal pool. Network-specific aliases
are added for every corresponding attachment.

The current installer appends the shared records to each container's local
record list. It deduplicates exact hostname/IP pairs with a set, writes
`IP<TAB>hostname` lines to `/tmp/etc-hosts`, and injects a startup command to
append that file to `/etc/hosts`. File order is unspecified. Hosts-file delivery
uses the generated startup script.

`demo_bundle.printEtcHostsRecords()` runs after compilation and prints shared
records only. These records do not update Base-layer nodes: `joinInternalNetwork()`
records an attachment, without registering or rendering an EtcHosts layer.
If emulator nodes need a bundle hostname, register the explicit record with
that layer before `emu.render()`.

## Lifecycle and generated files

```text
build/load B00 -> render emulator -> create DemoContainerBundle
-> supply network pools/ports -> register with Docker
-> compile emulator nodes -> configure bundle -> install prepared containers
```

The constructor creates two prepared containers. `configure()` calls the base
port check, assigns Compose attributes and attachments, registers aliases, and
stages application files. `docker.addContainerBundle()` only registers; Docker
later calls configure/install during `emu.compile()`. Avoid manually configuring
it again, because configuration appends records and attachments.

The app stages `/usr/local/bin/demo-message.sh`, but startup does not execute
that script. Its wrapper prints service/hostname information, then waits in
`sleep infinity`. The helper wrapper runs `exec sleep infinity`. In both cases,
the supplied `/bin/sh` delegation is not reached while the container stays up.
Hosts and route commands are inserted before the long-running commands.

Installation creates build contexts `output/demo-app.demo.seed` and
`output/demo-helper.demo.seed`. They contain Dockerfiles and staged files whose
names are MD5 hashes of their destination paths. COPY instructions restore the
paths, including `/tmp/etc-hosts`, `/new-entrypoint.sh`, and the app's message
script. Derived images currently install `iproute2` and `iputils-ping` through
apt, and the installer enables privileged mode.

## Automated verification

[example.yaml](example.yaml) runs the standard TestRunner lifecycle;
[test_runtime.py](test_runtime.py) uses `ComposeRuntimeTest` for configuration
checks, retried container commands, and a JSON summary. From the repository root:

```sh
python -B seedemu/testing/cli.py all examples/basic/A14_add_containerBundle/example.yaml --artifact-dir ci-artifacts/a14
```

The runner cleans declared generated files, compiles, builds, starts the project,
checks readiness, executes probes and the custom test, and attempts teardown
even on failure. The test checks both containers' static attachments and
wrappers, bridge IPAM, the published port, shared hostname resolution, both app
internal addresses and gateways, and the staged executable script. It does not
expect an HTTP server on 8090.

The manifest uses `standard_args: false` with positional `compile.args: [amd]`.
To select ARM64, update both that argument to `[arm]` and `platform` to `arm`.
Compilation and test subprocesses disable Python bytecode-cache generation.
Generated output remains under `output`; logs and `a14-runtime-test.json` are
written under the artifact directory. Individual runner stages (`compile`,
`build`, `up`, `probe`, `test`, `down`) can also be invoked for diagnosis.
