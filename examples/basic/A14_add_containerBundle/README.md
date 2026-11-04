# A14: Custom ContainerBundle

This example loads the B00 mini Internet and adds two Docker containers through
`DemoContainerBundle`. It demonstrates explicit network attachments, staged
files, hosts records, port publishing, and startup wrapping.

## Run

```sh
cd examples/basic/A14_add_containerBundle
python add_containerBundle.py amd
cd output
docker compose up --build -d
```

The script accepts `amd` (default) or `arm`. Run from this directory;
`base_internet.bin` and `output` are generated here.

| Service | Private bridge IP | Emulator IPs | Port mapping |
| --- | --- | --- | --- |
| `demo-app.demo.seed` | `172.31.0.10` | `10.151.0.16`, `10.152.0.16` | `8090:8080` |
| `demo-helper.demo.seed` | `172.31.0.11` | none | none |

The bridge is `demo_bundle_network`, subnet `172.31.0.0/24`, gateway
`172.31.0.1`. The first internal attachment sets the app's default gateway to
`10.151.0.254`. Choose unused addresses; no automatic allocation occurs.
The app prints a message and sleeps. There is no HTTP server on port 8080.

## Custom bundle API

`demoContainerBundle.py` creates its containers in `__init__`. Lookup keys are
logical names without suffixes: `bundle.getContainer("demo-app")` returns the
container whose `getHostname()` is `demo-app.demo.seed`.

The caller supplies pools through `addExternalNetwork()`,
`addInternalNetwork(asn=..., network="net0", ip_addresses=..., default_route=...)`,
and `setPorts()`. The subclass calls `super().configure()` for port validation,
then attaches both containers to the private bridge and the app to both
emulator networks. Both containers receive their peer's private bridge alias
through `bundle.addEtcHostsRecord(name, ip)`. The app additionally registers
`demo-app-local` at `127.0.0.1` through `app.addEtcHostsRecord(name, ip)`; that
alias is local to the app and is not copied to the helper. Installation merges
shared and local records without modifying either source list, removes duplicate
pairs in insertion order, writes `IP hostname` to `/tmp/etc-hosts`, and appends
the file to `/etc/hosts` at startup.

`setFile()` stages `/usr/local/bin/demo-message.sh`; the test executes it
explicitly. The app's startup wrapper prints its identity and sleeps. The helper
also uses a wrapper with a valid entrypoint to initialize hosts and stay running.

## Lifecycle

```text
render emulator -> create bundle -> supply networks/ports -> register with Docker
-> compile: configure bundle -> install bundle
```

`docker.addContainerBundle()` only registers the bundle. Do not call configure
manually before compilation: compilation calls it again and consumes ports.
Call `printEtcHostsRecords()` after successful compilation. Its output is
`IP<TAB>hostname` for shared bundle records only, excluding app-local records.

Bundle-local hosts records do not update emulator nodes. The current internal
join method adds an EtcHosts record during compilation, after rendering; that
record is too late to affect emulator nodes. Register emulator-node records
before `emu.render()`. See the [bundle API notes](../../../docs/designs/container_bundle.md).

## Automated test

From the repository root:

```sh
python seedemu/testing/cli.py all examples/basic/A14_add_containerBundle/example.yaml --artifact-dir ci-artifacts/a14
```

The manifest uses `standard_args: false` for the script's positional platform
argument. Change `compile.args` to `[arm]` for ARM64. `test_runtime.py` uses
`ComposeRuntimeTest` to check static attachments, port mapping, staged files,
peer hostname resolution and connectivity, internal addresses, and the default
route. It does not probe port 8090 as an HTTP endpoint.

Use a Linux Docker host supporting privileged containers. Reserve port 8090
and avoid overlapping bridge subnets. Stop with the runner's `down` command.
