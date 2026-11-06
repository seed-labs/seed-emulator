# User Manual: Visualization

- [Add the InternetMap bundle](#add-map)
- [Select ports](#ports)
- [Access the services](#access-map)

<a id="add-map"></a>
## Add the InternetMap bundle

`Docker()` no longer adds an Internet Map automatically. Create an
`InternetMap` after `emu.render()`, assign at least three host ports, and
register it with the Docker compiler before calling `emu.compile()`:

```python
from seedemu.compiler import Docker, Platform
from seedemu.containerBundle import InternetMap

emu.render()

docker = Docker(platform=Platform.AMD64)
internet_map = InternetMap(emu, ".map.seed")
internet_map.setPorts([8081, 8082, 8083])
docker.addContainerBundle(internet_map)

emu.compile(docker, "./output", override=True)
```

The bundle generates four services: an emulator API, a topology UI, a
geographic UI, and a traffic observer. The suffix distinguishes their Compose
service names and build directories from another bundle instance.

To let the emulator API reach an emulated network, attach it explicitly after
rendering:

```python
internet_map.addInternalNetwork(
    asn="151",
    network_name="net0",
    ip_addresses=["10.151.0.90"],
)
```

The selected address must be available on that network. If `default_route` is
omitted, the bundle reads the network's rendered default router.

<a id="ports"></a>
## Select ports

The first three entries passed to `setPorts()` have fixed roles:

| Position | Service |
| --- | --- |
| 1 | Traffic observer control port |
| 2 | Topology UI HTTP port |
| 3 | Geographic UI HTTP port |

Choose ports that are not already published by emulator nodes or other host
services. The compiler does not probe the host for port availability.

<a id="access-map"></a>
## Access the services

For `setPorts([8081, 8082, 8083])`, open:

- Topology UI: <http://127.0.0.1:8082/>
- Geographic UI: <http://127.0.0.1:8083/>
- Traffic observer control endpoint: `127.0.0.1:8081`

The traffic observer uses host networking, the host PID namespace, privileged
mode, Docker's socket, and Linux kernel/BPF mounts. Run the complete bundle on
a Linux Docker host that provides those facilities.

For a complete example, see
[B08 InternetMap bundle](../../examples/internet/B08_internet_map_bundle/README.md).
