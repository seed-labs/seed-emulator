# B08: InternetMap bundle with emulator access

This example loads [B00's mini Internet](../B00_mini_internet/README.md) and adds
one InternetMap deployment with a topology UI, geographic UI, emulator API, and
traffic observer. The API also joins AS151/net0, while the UIs use a private
Docker bridge and the observer uses host networking.

[InternetMap design](../../../docs/designs/internet_map.md) describes the shared
service/proxy implementation. This README is the walkthrough for the current
[internet_map_bundle.py](internet_map_bundle.py). For implementing a custom
bundle, see [A14](../../basic/A14_add_containerBundle/README.md) and the
[ContainerBundle design](../../../docs/designs/container_bundle.md).

## Services, ports, and addresses

The script constructs one `InternetMap(emu, ".map.seed.emu")` deployment.

| Logical key | Generated service/container | Private bridge IP | Other connectivity | Host endpoint |
| --- | --- | --- | --- | --- |
| `emulator_api_server` | `emulator_api_server.map.seed.emu` | `172.30.0.10` | AS151/net0 at `10.151.0.16`; Docker socket | No published API port; bridge port 7071 |
| `internetmap_toplogy` | `internetmap_toplogy.map.seed.emu` | `172.30.0.11` | Nginx proxies to API | `http://localhost:8092` |
| `internetmap_geo` | `internetmap_geo.map.seed.emu` | `172.30.0.12` | Nginx proxies to API and host observer | `http://localhost:8093` |
| `traffic_observer` | `traffic_observer.map.seed.emu` | none | Host network/PID and kernel mounts | Control port 8091 |

`toplogy` is the current spelling in the service key and image name. Use it
verbatim in Compose commands. Logical lookup keys omit the suffix, whereas
service names, container names, and build directories include it. The generated
name does not itself configure the container's OS hostname.

The current images are `handsonsecurity/seedemu-emulator-service:1.0`,
`handsonsecurity/seedemu-internet-toplogy:1.0`,
`handsonsecurity/seedemu-internet-map-geographic:1.0`, and
`handsonsecurity/seedemu-traffic-observer-service:1.0`.

Ports are configured explicitly:

```python
internet_map.setPorts([8091, 8092, 8093])
```

The implementation reads indexes 0, 1, and 2 as observer control, topology HTTP,
and geographic HTTP. It does not pop entries; only the first three are used.
The observer's port is conveyed by TRAFFIC_CONTROL_ADDR with host networking,
not by a Compose ports mapping. If Docker runs remotely, replace localhost in
the UI URLs with the Docker host address.

## Default bridge and explicit emulator attachment

This script does not call `addExternalNetwork()`. InternetMap configuration
registers its default `internetMap_network` bridge with subnet `172.30.0.0/24`
and gateway `172.30.0.1`. Backend and UIs take the first three static addresses
from the pool. A fourth address, `.13`, exists in the default pool but is unused
because the observer uses host networking.

The generated Compose network must contain IPAM for this subnet. The actual
Docker network name also includes the Compose project prefix. A name suffix
such as `.map.seed.emu` does not isolate the subnet or change its definition.

The emulator attachment is explicit:

```python
internet_map.addInternalNetwork(
    asn="151", network_name="net0", ip_addresses=["10.151.0.16"],
)
```

The topology is rendered before this call. Address availability is checked
against configured emulator interfaces, but the address is not allocated or
reserved. Omitting default_route requests the rendered network's gateway.
Only the API joins the first internal pool using its first IP; the UIs do not
join emulator networks, and the observer retains host networking. If a nonempty
gateway is found, startup replaces the API container's default route with it.

Without this internal attachment, the API still has its private bridge and
Docker socket; it simply lacks a direct interface on the emulator network.
This example uses explicit addInternalNetwork(), not an enable flag or an
automatic address allocator.

To customize the bridge, insert a call before registration/compilation:

```python
internet_map.addExternalNetwork(
    network_name="custom_map_network",
    prefix="172.40.0.0/24",
    ip_addresses=[f"172.40.0.{i}" for i in range(10, 14)],
    default_route="172.40.0.1",
)
```

The first supplied external pool is used. Validation requires four addresses,
including a slot for the host-network observer. If adding a second instance,
choose distinct suffixes, bridge names/subnets, internal IPs, and host ports;
the observers still access the same Docker host.

## Hosts aliases and proxies

The configured deployment registers these shared records:

| Alias | Address |
| --- | --- |
| `emulator_api_server-e.map.seed.emu` | `172.30.0.10` |
| `internetmap_toplogy.map.seed.emu` | `172.30.0.11` |
| `internetmap_geo.map.seed.emu` | `172.30.0.12` |
| `emulator_api_server.map.seed.emu` | `10.151.0.16` |

The external API alias includes `-e`; its generated name points to the explicit
internal address in this example. The current Bundle installer appends shared
records to each prepared container's local record list. Containers with startup
script processing enabled stage deduplicated `IP<TAB>hostname` lines in
`/tmp/etc-hosts` and append them to `/etc/hosts` at startup; line order is
unspecified. The observer is included in this shared-record distribution.
These records do not populate emulator-node EtcHosts files.

Both UIs proxy `/api/v1` and `/emulator/` requests to the API's **bridge** IP on
7071, even though it also has an emulator-facing interface. Nginx supports
WebSocket upgrade headers and serves the frontend SPA at `/`.
The geographic UI additionally maps `host.docker.internal` to `host-gateway`
and proxies `/traffic-observer/` to control port 8091 on the Docker host.
That Compose extra_hosts entry serves the host proxy; it is separate from the
bundle's shared aliases.

## Lifecycle and generated files

```text
generate/load B00 -> render emulator -> construct InternetMap
-> supply internal address/host ports -> register with Docker
-> compile emulator nodes -> configure InternetMap -> install prepared containers
```

`docker.addContainerBundle()` only registers the object. During compilation,
InternetMap validates inputs, selects the default bridge, configures addresses,
ports, proxies and aliases, then emits Compose fragments and build contexts.
Do not manually configure the same bundle again before compilation: configuration
appends attachment and hosts metadata.

`output` contains the emulator services plus four InternetMap service contexts.
COPY sources use MD5 hashes of destination paths. Relevant destinations include
`/tmp/etc-hosts`, `/new-entrypoint.sh`, and the UIs'
`/etc/nginx/conf.d/default.conf`. Startup preparation delegates to the configured
image entrypoint: `/start.sh` for the API by default, `/entrypoint.sh` for UIs,
and `/usr/local/bin/traffic-observer-entrypoint` for the observer.
Derived-image generation currently installs iproute2 and iputils-ping through apt
and enables privileged mode. The base images must support that build path.

## Automated verification

[example.yaml](example.yaml) defines the TestRunner lifecycle and published UI
HTTP probes. [test_runtime.py](test_runtime.py) uses `ComposeRuntimeTest` to
inspect generated configuration and run retried container commands. From the
repository root:

```sh
python -B seedemu/testing/cli.py all examples/internet/B08_internet_map_bundle/example.yaml --artifact-dir ci-artifacts/b08
```

The runner cleans declared output, compiles, builds, starts the project, checks
readiness, runs probes and the custom test, and attempts teardown even on failure.
Checks cover all four services, default bridge IPAM, the API's internal
attachment and gateway, UI port mappings and HTTP responses, Nginx targets,
bridge reachability, shared aliases, observer host-network/control-port
configuration, and a TCP connection to observer port 8091. They do not validate
actual packet capture or traffic control.

The HTTP probes use localhost:8092/8093, so run the lifecycle on the Linux Docker
host; a remote Docker daemon needs corresponding probe URL changes. Required
kernel facilities and mounts are the same as for manual startup. The observer
running-state check is not a substitute for testing capture behavior.

The manifest uses `standard_args: false` and `compile.args: [amd]`. For ARM64,
change that argument to `[arm]` and `platform` to `arm`, subject to image support.
Compilation and test subprocesses disable Python bytecode-cache generation.
Logs and `b08-runtime-test.json` are written under the artifact directory.
Individual stages (`compile`, `build`, `up`, `probe`, `test`, `down`) are also
available for diagnosis.
