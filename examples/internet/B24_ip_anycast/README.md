# IP Anycast

This example demonstrates IP anycast using the `B00_mini_internet` topology as
the base Internet. IP anycast lets multiple sites use the same IP address. BGP
then decides which site receives traffic for that address.

One well-known use case is DNS root service. For example, one logical DNS root
server can be deployed at many physical locations, while clients still send
queries to one stable IP address. The network routes each client to one of the
available sites.

## Topology

The example adds `AS180` to the B00 mini Internet. `AS180` has two disconnected
sites:

```text
IX100 side:
  host-0: 10.180.0.100
  router0: connected to IX100

IX105 side:
  host-1: 10.180.0.100
  router1: connected to IX105
```

Both hosts use the same address, `10.180.0.100`, but they are on different
internal networks:

```python
as180.createNetwork("net0", "10.180.0.0/24")
as180.createNetwork("net1", "10.180.0.0/24")

as180.createHost("host-0").joinNetwork("net0", address="10.180.0.100")
as180.createHost("host-1").joinNetwork("net1", address="10.180.0.100")
```

The two sites connect to the Internet at different IXes:

```python
as180.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
ebgp.addPrivatePeerings(100, [3, 4], [180], PeerRelationship.Provider)

as180.createRouter("router1").joinNetwork("net1").joinNetwork("ix105")
ebgp.addPrivatePeerings(105, [2, 3], [180], PeerRelationship.Provider)
```

Each anycast host runs a small web server with different content. This makes
the selected anycast site visible during testing:

```text
host-0 response contains: ix100-west
host-1 response contains: ix105-east
```

## Self-Managed Docker Networks

The Docker compiler must use `selfManagedNetwork=True` for this example.
Without this option, Docker manages the networks and does not allow two
different Docker networks to use the same IP prefix. The example entrypoint
sets this option automatically:

```python
Docker(selfManagedNetwork=True, platform=platform)
```

## Standard Arguments

The entrypoint supports the standard example arguments used by
`seedemu/testing/cli.py`:

```sh
python examples/internet/B24_ip_anycast/ip_anycast.py --platform amd --output examples/internet/B24_ip_anycast/output
```

The legacy platform argument is also accepted:

```sh
python examples/internet/B24_ip_anycast/ip_anycast.py amd
```

Useful options:

```text
--platform amd|arm
--output PATH
--dumpfile PATH
--hosts-per-as N
--skip-render
--no-override
```

## Test Runner

Use the standardized runner from the repository root:

```sh
python seedemu/testing/cli.py clean examples/internet/B24_ip_anycast/example.yaml
python seedemu/testing/cli.py compile examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
python seedemu/testing/cli.py build examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
python seedemu/testing/cli.py up examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
python seedemu/testing/cli.py probe examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
python seedemu/testing/cli.py test examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
python seedemu/testing/cli.py down examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/internet/B24_ip_anycast/example.yaml --artifact-dir ci-artifacts/b24
```

## Runtime Checks

The declarative probes check the externally visible anycast behavior:

- a host in `AS150` reaches `10.180.0.100` and receives the IX100-side web
  response;
- a host in `AS170` reaches `10.180.0.100` and receives the IX105-side web
  response.

The custom `test_runtime.py` adds more specific validation:

- both AS180 hosts exist and have the same anycast address;
- both local web servers are running and expose their site markers;
- both AS180 routers have the anycast prefix in BIRD;
- representative clients from different parts of the mini Internet reach
  different anycast sites.
