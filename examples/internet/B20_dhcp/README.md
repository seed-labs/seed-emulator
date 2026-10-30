# DHCP

This example demonstrates how to deploy DHCP servers inside the SEED Emulator
and how to configure hosts to obtain their IP addresses through DHCP.

The example starts from the `B00_mini_internet` topology, then adds DHCP service
to two stub ASes:

- AS151 has DHCP server `dhcp-server-01`.
- AS161 has DHCP server `dhcp-server-02`.
- AS151 has two DHCP clients: `dhcp-client-01` and `dhcp-client-02`.
- AS161 has two DHCP clients: `dhcp-client-03` and `dhcp-client-04`.

The tests for this example focus only on DHCP behavior. They do not repeat B00's
mini-Internet reachability tests.

## Step 1: Deploy DHCP Servers

Create the DHCP service and install two DHCP server virtual nodes:

```python
dhcp = DHCPService()

# Default DHCP range: x.x.x.101 - x.x.x.120.
# Custom AS151 DHCP range: x.x.x.125 - x.x.x.140.
dhcp.install("dhcp-01").setIpRange(125, 140)
dhcp.install("dhcp-02")
```

Customize their display names for visualization:

```python
emu.getVirtualNode("dhcp-01").setDisplayName("DHCP Server 1")
emu.getVirtualNode("dhcp-02").setDisplayName("DHCP Server 2")
```

Create physical hosts to run the DHCP servers:

```python
as151 = base.getAutonomousSystem(151)
as151.createHost("dhcp-server-01").joinNetwork("net0")

as161 = base.getAutonomousSystem(161)
as161.createHost("dhcp-server-02").joinNetwork("net0")
```

Bind the DHCP virtual nodes to those physical hosts:

```python
emu.addBinding(Binding("dhcp-01", filter=Filter(asn=151, nodeName="dhcp-server-01")))
emu.addBinding(Binding("dhcp-02", filter=Filter(asn=161, nodeName="dhcp-server-02")))
```

## Step 2: Create DHCP Clients

To make a host use DHCP instead of a static address, join the network with
`address="dhcp"`:

```python
as151.createHost("dhcp-client-01").joinNetwork("net0", address="dhcp")
as151.createHost("dhcp-client-02").joinNetwork("net0", address="dhcp")

as161.createHost("dhcp-client-03").joinNetwork("net0", address="dhcp")
as161.createHost("dhcp-client-04").joinNetwork("net0", address="dhcp")
```

The SEED Emulator adds the DHCP client software and a startup helper script to
request a lease when the container starts.

## DHCP Address Ranges

The default address ranges are:

- Host static address range: `.71` to `.99`
- DHCP address range: `.101` to `.120`
- Router address range: `.254` downward

`DHCPServer.setIpRange()` changes the DHCP range for the network served by that
DHCP server. In this example:

- AS151 uses the custom DHCP range `10.151.0.125` to `10.151.0.140`.
- AS161 uses the default DHCP range `10.161.0.101` to `10.161.0.120`.

To change the entire network allocation policy, use `Network.setHostIpRange()`,
`Network.setDhcpIpRange()`, and `Network.setRouterIpRange()`.

## Standard Arguments

```sh
python examples/internet/B20_dhcp/dhcp.py amd
python examples/internet/B20_dhcp/dhcp.py --platform amd --output examples/internet/B20_dhcp/output
python examples/internet/B20_dhcp/dhcp.py --dumpfile examples/internet/B20_dhcp/dhcp.bin
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
python seedemu/testing/cli.py all examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
```

The lifecycle can also be run step by step:

```sh
python seedemu/testing/cli.py clean examples/internet/B20_dhcp/example.yaml
python seedemu/testing/cli.py compile examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
python seedemu/testing/cli.py build examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
python seedemu/testing/cli.py up examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
python seedemu/testing/cli.py probe examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
python seedemu/testing/cli.py test examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
python seedemu/testing/cli.py down examples/internet/B20_dhcp/example.yaml --artifact-dir ci-artifacts/b20-dhcp
```

The declarative probes check representative DHCP clients:

- An AS151 client receives an address from `10.151.0.125` to `10.151.0.140`.
- An AS161 client receives an address from `10.161.0.101` to `10.161.0.120`.
- DHCP clients can reach their local default routers.

The custom `test_runtime.py` program checks DHCP-specific deployment details:

- DHCP server containers are generated and `dhcpd` is running.
- AS151's DHCP server config contains the custom range.
- AS161's DHCP server config contains the default range.
- All four DHCP clients have the generated DHCP client helper.
- All four DHCP clients receive addresses from the expected ranges.
- All four DHCP clients install the expected default route.
