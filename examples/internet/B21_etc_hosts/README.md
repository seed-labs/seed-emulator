# EtcHosts

This example demonstrates how to enable local name resolution using the
`EtcHosts` layer. The layer writes emulator node names and custom hostnames into
each container's `/etc/hosts` file, so hosts can resolve names without deploying
DNS.

The example starts from the `B00_mini_internet` topology, then adds one new host
in AS152:

- Host name: `database`
- IP address: `10.152.0.4`
- Custom hostname: `database.com`

The tests for this example focus only on `/etc/hosts` behavior. They do not
repeat B00's mini-Internet reachability tests.

## Create A Host With A Custom Hostname

The default hostname of a node is based on its scope and node name. For example,
a node named `host_0` in AS154 has a generated hostname such as `154-host_0`.

We can add additional hostnames using `addHostName()`:

```python
base: Base = emu.getLayer("Base")
as152 = base.getAutonomousSystem(152)
as152.createHost("database").joinNetwork("net0", address="10.152.0.4").addHostName("database.com")
```

## Add The EtcHosts Layer

After the custom hostname is configured, add the `EtcHosts` layer:

```python
emu.addLayer(EtcHosts())
```

When the emulator is rendered, the layer creates `/etc/hosts` entries for the
emulator hosts. Every generated container should then be able to resolve
`database.com` to `10.152.0.4`.

## Standard Arguments

```sh
python examples/internet/B21_etc_hosts/etc_hosts.py amd
python examples/internet/B21_etc_hosts/etc_hosts.py --platform amd --output examples/internet/B21_etc_hosts/output
python examples/internet/B21_etc_hosts/etc_hosts.py --dumpfile examples/internet/B21_etc_hosts/etc_hosts.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## Standardized TestRunner Lifecycle

Run the full lifecycle from the repository root:

```sh
python seedemu/testing/cli.py all examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
```

The lifecycle can also be run step by step:

```sh
python seedemu/testing/cli.py clean examples/internet/B21_etc_hosts/example.yaml
python seedemu/testing/cli.py compile examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
python seedemu/testing/cli.py build examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
python seedemu/testing/cli.py up examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
python seedemu/testing/cli.py probe examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
python seedemu/testing/cli.py test examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
python seedemu/testing/cli.py down examples/internet/B21_etc_hosts/example.yaml --artifact-dir ci-artifacts/b21-etc-hosts
```

The declarative probes check that representative hosts can resolve
`database.com` to `10.152.0.4`.

The custom `test_runtime.py` program checks `/etc/hosts`-specific behavior:

- The `database` host is generated in AS152.
- The `database` host has address `10.152.0.4`.
- Representative containers contain a `database.com` entry in `/etc/hosts`.
- Representative containers resolve `database.com` to `10.152.0.4`.
- A representative host can reach the database host by custom hostname.
