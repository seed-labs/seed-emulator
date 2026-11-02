# InternetMap design

`seedemu.containerBundle.InternetMap` extends `ContainerBundle` to provide
an emulator API, topology UI, geographic UI, and traffic observer. See the
[ContainerBundle design](container_bundle.md) for shared lifecycle behavior.

## Services and construction

| Logical service name | Role | Network behavior |
| --- | --- | --- |
| `seedemu_emulator_service_backend` | REST and WebSocket APIs | Bundle network; optionally emulator network |
| `seedemu_internet_map_toplogy` | Topology frontend | Bundle network |
| `seedemu_internet_map_geographic` | Geographic frontend | Bundle network and `host.docker.internal` mapping |
| `seedemu_traffic_observer_service_backend` | Host traffic capture | `network_mode: host` |

The constructor accepts `emulator` and `suffix="map.seed"`. It creates four
prepared containers, sets `_default_external_network = DEFAULT_NETWORK`,
requires three host ports, and requests one emulator-network address. Internal
network access starts disabled; construction does not allocate an address.

Registration keys, Compose service keys, container names, hostnames, and build
folders use the logical name plus the suffix. Use distinct suffixes, external
networks, subnets, and host ports for separate instances.

## Optional internal network

Call `enableInternalNetwork()` before compilation to enable emulator access:

```python
internet_map = InternetMap(emu, ".map.seed")
internet_map.enableInternalNetwork()
internet_map.setPorts([8081, 8082, 8083])
docker.addContainerBundle(internet_map)
```

This method sets a flag and returns the bundle. During `configure()`, only the
API backend joins the internal network. If no manual internal network has
been supplied, `allocateEmuNetworkAddress()` reserves one address on a rendered
host network, starting at network-address offset 10. It skips occupied and
reserved addresses and the gateway. The selected `ip_addresses[0]` and
`default_route` are passed explicitly to `joinInternalNetwork()`, together
with the backend's own hostname. A usable network with enough capacity is
required when this option is enabled.

To choose the internal attachment explicitly before compilation:

```python
internet_map.setDefaultInternalNetwork(
    name="net_150_net0",
    ip_addresses=["10.150.0.10"],
    default_route="10.150.0.254",
)
internet_map.enableInternalNetwork()
```

The manual address must be free; the setter does not reserve or validate it.
When a gateway is supplied, generated startup commands replace the backend's
Docker default route. Its build context is enabled for this startup setup.
Both frontends continue to reach the API through the external bundle network.

## Configuration and compilation

`configure()` performs these steps:

1. Calls the base port validation using the constructor's requirement of three
   ports. The observer consumes the last supplied port, the topology frontend
   the next, and the geographic frontend the next. The API uses internal port
   `7071` without a host-published port.
2. Configures the observer with host networking, privileged mode, host PID,
   kernel/BPF mounts, and the Docker socket. It skips bridge attachment.
3. Attaches the API and both frontends to the external bundle network with
   static addresses in container creation order.
4. Configures the API image, Docker socket, and production environment, and
   attaches its optional internal network.
5. Configures frontend dependencies using the suffixed backend service key.
   Both Nginx upstreams target the API's external-network static IP on `7071`.
   The geographic proxy also targets the configured traffic-observer endpoint.
6. Stages Nginx configuration and `/etc/hosts` mappings for both frontends.
   Their configured startup script path is `/entrypoint.sh`; shared
   `PreparedContainer` installation handles startup wrapping and staged files.

The external network can be overridden before compilation:

```python
internet_map.setDefaultExternalNetwork(
    name="internetMap_network",
    prefix="172.30.0.0/24",
    ip_addresses=[f"172.30.0.{i}" for i in range(10, 14)],
    default_router="172.30.0.1",
)
```

The address list must cover all four prepared containers, although the
observer's entry remains unused because it uses host networking. The compiler
calls `configure()` and `install()` to generate build contexts and Compose YAML.
