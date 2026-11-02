# B08: Two InternetMap bundles

This example demonstrates how to register two independent `InternetMap`
bundles in one SEED Emulator compilation. Both bundles provide topology,
geographic, and traffic visualization services, but they use different
container suffixes, Docker networks, and host-port ranges.

## Running the example

```bash
cd examples/internet/B08_internet_map_bundle
python internet_map_bundle.py
```

The script defaults to AMD64. Use `python internet_map_bundle.py amd` or
`python internet_map_bundle.py arm` to select the target platform explicitly.

It calls `mini_internet.run(dumpfile="./base_internet.bin")`, loads that
component into an `Emulator`, and renders it before creating the bundles.
It then registers both bundles with `Docker(platform=platform)` and writes
the generated Compose project to `output` with `override=True`:

```bash
cd output
docker compose up --build
```

The port pools are consumed from the end of each list. Only three ports per
bundle are used:

| Instance | Topology UI | Geographic UI | Traffic observer |
| --- | --- | --- | --- |
| `.map.seed` | `http://localhost:8087` | `http://localhost:8086` | `8088` |
| `.map.seed.emu` | `http://localhost:8097` | `http://localhost:8096` | `8098` |

The API backend uses port `7071` on the bundle network and does not publish
a separate host port. The observer uses host networking; both instances
capture traffic from the same Docker host.

## The two bundle instances

The first instance is the baseline configuration:

```python
bundle = InternetMap(emu, ".map.seed")
bundle.setDefaultExternalNetwork(
    name="internetMap_network",
    prefix="172.30.0.0/24",
    ip_addresses=[f"172.30.0.{i}" for i in range(10, 14)],
    default_router="172.30.0.1",
)
bundle.setPorts(list(range(8081, 8089)))
docker.addContainerBundle(bundle)
```

This bundle uses the `172.30.0.0/24` bridge network and the `8081`–`8088`
host-port pool. Its services communicate through the bundle network. The
emulator-service backend is not attached to an emulator network by this
instance.

The second instance uses independent names and addresses:

```python
bundle_join_emu_network = InternetMap(emu, ".map.seed.emu")
bundle_join_emu_network.setDefaultExternalNetwork(
    name="internetMap_network_emu",
    prefix="172.40.0.0/24",
    ip_addresses=[f"172.40.0.{i}" for i in range(10, 14)],
    default_router="172.40.0.1",
)
bundle_join_emu_network.enableInternalNetwork()
bundle_join_emu_network.setPorts(list(range(8091, 8099)))
docker.addContainerBundle(bundle_join_emu_network)
```

The suffix `.map.seed.emu` prevents Compose service and hostname collisions.
Registration keys, `container_name` values, and build directories also include
the suffix. For example, the second API service is named
`seedemu_emulator_service_backend.map.seed.emu`.
The `172.40.0.0/24` network and `8091`–`8098` port pool prevent address and
host-port conflicts with the first instance.

`enableInternalNetwork()` is the functional difference between the two
instances. It sets a flag; during `configure()`, the bundle reserves one free
address starting at network-address offset 10 and passes the stored network,
first `ip_addresses` entry, backend hostname, and optional gateway to
`seedemu_emulator_service_backend.joinInternalNetwork(...)`. The backend then
has two network attachments:

1. The bundle bridge network, used by the visualization frontends and other
   InternetMap services.
2. A selected emulator network, used to communicate with the emulated network
   and its emulator service API. If a default route is available, the startup
   script also installs the route through the emulator gateway.

The first bundle remains bridge-only, so it is useful as a comparison showing
the default InternetMap connectivity model.

The second bundle does not call `setDefaultInternalNetwork()`, so its internal
address is selected automatically during compilation. The `.10` starting
point is relative to the selected network address; occupied addresses, the
gateway, and earlier bundle reservations are skipped. A rendered host network
with at least one free eligible address is required. The frontends retain
their external-network attachments and proxy to the backend's static IP on
that network. The traffic observer remains on host networking.

## Registration lifecycle

Both bundles are registered independently:

```python
docker.addContainerBundle(bundle)
docker.addContainerBundle(bundle_join_emu_network)
emu.compile(docker, "./output", override=True)
```

During compilation, each bundle validates its port pool, assigns static
addresses, configures its prepared services, and emits its own network definition. The
different suffixes, network names, subnets, and host-port ranges allow both
bundles to coexist in the generated Compose project.

## InternetMap design

This README focuses on the differences demonstrated by this example. For the
complete `InternetMap` service topology, lifecycle, reverse-proxy setup,
network attachments, optional emulator-network integration, and generated
startup files, see the [InternetMap design document](../../../docs/designs/internet_map.md).
