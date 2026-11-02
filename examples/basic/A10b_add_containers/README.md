# A10b: Custom ContainerBundle

This example demonstrates how to attach a custom group of Docker containers to a SEED Emulator using `ContainerBundle`.

The example builds three autonomous systems connected through Internet Exchange 100. It then renders the emulator, creates a `DemoContainerBundle`, configures its networks and ports, and registers it with the Docker compiler.

## Running

```bash
cd examples/basic/A10b_add_containers
python add_containerBundle.py
```

The generated Docker files are written to `output`. Start them with:

```bash
cd output
docker compose up --build
```

The bundle maps host port `8090` to container port `8080`. The demo prints a
message and sleeps; it does not start an HTTP server. Pass `amd` (the default)
or `arm` as the script argument to select the target platform.

## Bundle lifecycle

Import the bundle classes from `seedemu.containerBundle`:

```python
from seedemu.containerBundle import ContainerBundle
```

The normal lifecycle is:

```text
create bundle -> configure bundle -> register bundle -> compile emulator
```

`docker.addContainerBundle(bundle)` registers the bundle. During `emu.compile()`, the compiler calls the bundle's `configure()` and `install()` methods to generate Compose services, networks, Dockerfiles, startup scripts, and staged files.

## ContainerBundle API

Useful bundle methods include:

```python
bundle.getContainer("service-name" + bundle.getSuffix())
bundle.getContainers()
bundle.getEmulator()
bundle.getSuffix()
bundle.getDefaultExternalNetwork()
bundle.setDefaultInternalNetwork("net_151_net0", ["10.151.0.16"], "10.151.0.254")
bundle.getDefaultInternalNetwork()
bundle.setPorts([8090])
bundle.getPorts()
bundle.getInternalHostnameIpMappings()
bundle.getExternalHostnameIpMappings()
```

`getContainer()` returns a `PreparedContainer`. A custom bundle can configure it with:

```python
container.setContentAttribute({"image": "busybox:latest"})
container.joinInternalNetwork(network, hostname, ip_address, default_route)
container.joinExternalNetwork(network, hostname, ip_address)
container.setFile("/start.sh", "#!/bin/sh\n...")
container.setEtcHosts("10.0.0.10 example\n")
```

`setContentAttribute()` updates the Compose service definition. The network methods add network attachments and static addresses. `setFile()` stages a file for the generated image, and `setEtcHosts()` stages host entries that are appended during startup.

## Custom bundle pattern

This example also defines `DemoContainerBundle`, a concrete subclass that is
defined in this example. It creates two `PreparedContainer`
instances and demonstrates the main extension points in one run:

- `setContentAttribute()` and static external-network attachments
- `getContainer()`, `getContainers()`, `getSuffix()`, and network mapping accessors
- `allocateEmuNetworkAddress()`, `getDefaultInternalNetwork()`, and explicit
  `joinInternalNetwork()` arguments
- `setEtcHosts()` and `setFile()` for generated container files
- `setEntrypointWrapper()` for startup commands and a custom entrypoint

The demo bundle uses a separate `172.31.0.0/24` bridge network and publishes
one host port. The script explicitly attaches `demo-app` to `net_151_net0` at
`10.151.0.16`, with gateway `10.151.0.254`. If this manual selection is removed,
`configure()` attempts automatic allocation. Internal attachment is required
by this demo; it is not skipped on allocation failure.

```python
class ExampleBundle(ContainerBundle):
    def __init__(self, emulator, suffix=".example"):
        super().__init__(emulator=emulator, suffix=suffix)
        self._createContainer("example-service", suffix)

    def configure(self):
        self._required_port_number = 1
        super().configure()
        service = self.getContainer("example-service" + self.getSuffix())
        service.setContentAttribute({
            "image": "busybox:latest",
            "command": "sleep infinity",
        })
```

Subclasses create containers in `__init__`, configure their services in `configure()`, and should call `super().configure()` so port validation is preserved.

### Detailed `DemoContainerBundle` walkthrough

`DemoContainerBundle` creates two `PreparedContainer` objects in its
constructor:

```python
class DemoContainerBundle(ContainerBundle):
    def __init__(self, emulator, suffix=".demo.seed"):
        super().__init__(emulator=emulator, suffix=suffix)
        self._createContainer("demo-app", suffix)
        self._createContainer("demo-helper", suffix)
        self._required_emu_network_address_number = 1
        self._required_port_number = 1
```

`demo-app` is the main service and publishes a host port. `demo-helper` is a
second service used to demonstrate hostname mappings. The suffix is appended
to registration keys, Compose service keys, container names, hostnames, and
build-context directories. The services are `demo-app.demo.seed` and
`demo-helper.demo.seed`.

The constructor sets both required counts to `1`. During `configure()`, it calls
`super().configure()` for port validation, obtains its prepared containers,
and assigns Compose attributes. The app consumes one port from the configured
pool and maps it to container port `8080`; the helper stays alive with
`sleep infinity`.

The complete registration code is:

```python
demo_bundle = DemoContainerBundle(emu, ".demo.seed")
demo_bundle.setDefaultExternalNetwork(
    name="demo_bundle_network",
    prefix="172.31.0.0/24",
    ip_addresses=["172.31.0.10", "172.31.0.11"],
    default_router="172.31.0.1",
)
demo_bundle.setPorts([8090])
demo_bundle.setDefaultInternalNetwork(
    name="net_151_net0",
    ip_addresses=["10.151.0.16"],
    default_route="10.151.0.254",
)
demo_bundle.getInternalHostnameIpMappings()
demo_bundle.getExternalHostnameIpMappings()
docker.addContainerBundle(demo_bundle)
```

The calls perform these steps:

1. `DemoContainerBundle(emu, ".demo.seed")` creates and registers the two
   prepared services.
2. `setDefaultExternalNetwork()` creates the private `172.31.0.0/24` bridge network.
   Addresses are assigned in creation order: `demo-app` receives
   `172.31.0.10`, and `demo-helper` receives `172.31.0.11`.
3. `setPorts([8090])` supplies the host-port pool. The app consumes `8090`,
   producing the mapping `8090:8080`.
4. `setDefaultInternalNetwork()` stores the manual internal attachment. The
   network must exist and the address must be free; the setter does not
   validate or reserve addresses.
5. The mapping accessors return copies of hostname/IP mappings. These are
   empty before compilation because no containers have joined networks yet.
6. `docker.addContainerBundle()` registers the bundle. It does not start
   containers; `emu.compile()` later calls `configure()` and `install()`.

The custom bundle uses its own Docker network (`172.31.0.0/24`) and host port (`8090`).

Inside `configure()`, both containers join the custom network with static
addresses. The app uses the manual internal selection when supplied; otherwise
it requests one automatically:

```python
if not self._default_internal_network:
    self.allocateEmuNetworkAddress()
app.joinInternalNetwork(
    hostname=app.getHostname(),
    network=self._default_internal_network["network"],
    ip_address=self._default_internal_network["ip_addresses"][0],
    default_route=self._default_internal_network["default_route"],
)
```

`allocateEmuNetworkAddress()` returns the bundle on success, or `None` when no
network has enough capacity. It stores an internal network dictionary with an
`ip_addresses` list. Allocation starts at network-address offset 10 and skips
occupied and reserved addresses. Select one address for `joinInternalNetwork()`.
The app receives a second network attachment and route setup through the
supplied gateway; the helper remains on the bundle network. The current code
does not check allocation failure before reading the stored dictionary, so
automatic mode requires a rendered host network with enough capacity.

The example also demonstrates generated files and startup wrapping:

```python
app.setEtcHosts(f"{helper.getHostname()} {network['ip_addresses'][1]}\n")
app.setFile(
    "/usr/local/bin/demo-message.sh",
    "#!/bin/sh\necho 'ContainerBundle demo is running'\n",
)
app.setEntrypointWrapper(
    original_entrypoint="/bin/sh",
    commands=[
        "echo \"service=$0 hostname=$(hostname)\"",
        "sleep infinity",
    ],
)
```

`setEtcHosts()` stages host entries for startup, `setFile()` adds a file to the
generated image context, and `setEntrypointWrapper()` runs preparation commands
before delegating to the base image entrypoint.
The staged `demo-message.sh` is not executed by the wrapper. The wrapper prints
the service/hostname message and runs `sleep infinity`.

## Troubleshooting

- Too few ports: call `setPorts()` before registering the bundle.
- Invalid static addresses: check subnet membership, uniqueness, and gateway exclusion.
- Network reachability problems: render the emulator before compilation and verify the emulated host's default route.
- Port conflicts: choose a different host-port range and regenerate `output`.
- Manual attachment failure: verify `net_151_net0`, the availability of
  `10.151.0.16`, and gateway `10.151.0.254` in the rendered topology.
- No HTTP response on `8090`: the demo publishes a port but starts no server.
