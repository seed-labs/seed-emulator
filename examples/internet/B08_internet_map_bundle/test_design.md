# B08 runtime test design

## Expected containers

| Container | Expected connectivity | Expected service |
| --- | --- | --- |
| `emulator_api_server.map.seed.emu` | `172.30.0.10`, `10.151.0.16` | Emulator API on TCP 7071 |
| `internetmap_toplogy.map.seed.emu` | `172.30.0.11` | Topology UI on container TCP 80, host TCP 8092 |
| `internetmap_geo.map.seed.emu` | `172.30.0.12` | Geographic UI on container TCP 80, host TCP 8093 |
| `traffic_observer.map.seed.emu` | Host network and PID namespace | Observer control service on host TCP 8091 |

## Runtime checks

### Container state and interfaces

- All four containers are running and are not restarting.
- The API has live addresses `172.30.0.10` and `10.151.0.16`.
- The topology and geographic containers have `172.30.0.11` and
  `172.30.0.12`, respectively, and no emulator-network address.
- The observer uses the host network and has no `internetMap_network` interface.
- The API default route uses `10.151.0.254` and the gateway is reachable.
- Both UI containers can reach API address `172.30.0.10` and TCP port 7071.

### Ports and service access

- Docker reports host TCP 8092 mapped to topology TCP 80.
- Docker reports host TCP 8093 mapped to geographic TCP 80.
- The API has no host-published port for TCP 7071.
- `http://127.0.0.1:8092/` returns HTTP 200 and nonempty topology UI content.
- `http://127.0.0.1:8093/` returns HTTP 200 and nonempty geographic UI content.
- Host TCP 8091 accepts an observer connection, and `GET /healthz` through
  `http://127.0.0.1:8093/traffic-observer/healthz` returns HTTP 204.

### Nginx checks

Inspect `/etc/nginx/conf.d/default.conf` inside both running UI containers. Do
not infer configuration correctness only from an HTTP 200 response or from the
generated build context.

For `internetmap_toplogy.map.seed.emu` and
`internetmap_geo.map.seed.emu`:

- Verify the file exists, is nonempty, and is included in the active output of
  `nginx -T`. Run `nginx -t` and verify Nginx listens on TCP 80.
- Obtain the API container's actual `internetMap_network` address independently
  with `docker inspect`. It must be `172.30.0.10`, and the active Nginx
  configuration must contain exactly one API endpoint:
  `server 172.30.0.10:7071;`.
- Reject stale, loopback, UI-container, emulator-network, or duplicate API
  endpoints. In particular, `172.30.0.11`, `172.30.0.12`, and `10.151.0.16`
  must not be configured as the API upstream server.
- Verify `location ^~ /api/v1` proxies to
  `http://seedemu_emulator_service_backend` without stripping `/api/v1`, while
  `location ^~ /emulator/` proxies to
  `http://seedemu_emulator_service_backend/` with the intended prefix rewrite.
- Verify HTTP/1.1 and the Upgrade/Connection forwarding headers are present for
  WebSocket requests.
- From each UI container, establish a TCP connection to the configured
  `172.30.0.10:7071` endpoint. Valid syntax with an unreachable service IP is a
  failure.

For `internetmap_geo.map.seed.emu` additionally:

- Verify exactly one `traffic_observer` upstream contains
  `server host.docker.internal:8091;`.
- Verify `location ^~ /traffic-observer/` uses
  `proxy_pass http://traffic_observer/;`. The trailing slash is required to
  remove the public prefix before forwarding.
- Resolve `host.docker.internal` inside the geographic container, compare the
  result with its Docker host-gateway mapping, and establish a TCP connection
  to port 8091.

When a check fails, print the container name, configuration path, expected
upstream, actual matching `server` or `proxy_pass` lines, and the `nginx -t` or
connection error. Print the entire configuration only when the matching lines
cannot identify the problem.

## API and UI test implementation

Use three test files with one public entry point:

| Program | Responsibility |
| --- | --- |
| `test_runtime.py` | Check the running containers and then execute `test_api.py` and `test_ui.py` |
| `test_api.py` | Test Emulator API and Traffic Observer HTTP/WebSocket interfaces |
| `test_ui.py` | Test the topology Map and geographic 3D interfaces in a real browser |

Only `test_runtime.py` is registered in `example.yaml`. Running it executes the
whole suite in this order:

1. Runtime container and Nginx checks.
2. `test_api.py`.
3. `test_ui.py`.

The two child files remain directly executable for diagnosis. The parent test
returns nonzero when any part fails, but still runs independent later groups
when possible so one invocation reports both API and UI problems.

### Runtime implementation

Use `ComposeRuntimeTest`, `docker inspect`, and commands inside the running
containers. Verify live state instead of parsing the generated Compose file.
Implement the container, interface, route, port, hosts, label, mount, process,
connectivity, and **Nginx checks** described above in `test_runtime.py`.

### API implementation

Use Python HTTP/JSON support for ordinary requests and a WebSocket client for
packet events. Send Emulator API requests through both frontend Nginx proxies.
Test these read-only interfaces:

- `GET /api/v1/container`: container identities, state, labels, networks, and
  addresses, including the labeled-container discovery check under **Map
  labels**.
- `GET /api/v1/network`: network identities and metadata.
- `GET /api/v1/container/<id>`: one container's details.
- `GET /api/v1/container/<id>/net`: current network state without changing it.
- Unknown paths and nonexistent container IDs: API error handling.
- WebSocket upgrade through the Nginx proxy.

The same file tests the Traffic Observer interfaces described in **Traffic
observer and geographic capture** below. It must restore filter and recording
state during cleanup.

### UI implementation

Use Playwright with headless Chromium. Prefer stable `data-testid` selectors
and condition-based waits; do not use screenshot comparison, canvas pixel
comparison, or fixed sleeps.

Test the Topology Map at `http://127.0.0.1:8092/pro/map`:

- Page loading, static resources, API requests, and required WebSockets.
- Topology nodes and networks.
- Search by node name, IP address, and ASN.
- Node details and consistency with the Emulator API.
- Node/network filtering, zoom, pan, selection, and node dragging.
- Dashboard navigation and direct route refresh.

Test Geographic 3D at `http://127.0.0.1:8093/pro/map/3d`:

- Cesium initialization and 3D topology.
- Overview counts and node details.
- Search by node name, IP address, and ASN.
- AS and IX filters.
- Host, Router, Network, IX, label, hover-detail, node-scale, and link-scale
  controls.
- Globe rotation, zoom, hover, and node selection.
- Traffic filter, live packet/flow display, recording, stop, and replay.
- Overview, Settings, and Traffic Replay tabs; dock minimize/restore.
- Direct route refresh and desktop/narrow viewport layouts.

All three programs print the failed functional checkpoint, request or UI
operation, expected and actual result, and a short error message to the
terminal. They do not save screenshots, traces, videos, console logs, or
request records.

### Traffic observer and geographic capture

- The observer can access `/sys/kernel/debug`, `/sys/fs/bpf`, the read-only
  Docker socket, and writable `/data/pcap`.
- The API can access its read-only Docker socket.
- Observer logs contain no BPF verifier, mount, permission, or startup error.

Use the geographic proxy prefix
`http://127.0.0.1:8093/traffic-observer/` for HTTP and
`ws://127.0.0.1:8093/traffic-observer/ws/packets` for packet events. Nginx
removes `/traffic-observer/` before forwarding to observer port 8091.

Test the control API first:

1. `GET /healthz` returns HTTP 204.
2. `PUT /interfaces` refreshes Docker interface discovery. The JSON response has
   a nonempty `interfaces` value and `discoveredContainerInterfaces > 0`.
3. `GET /interfaces` returns the same current mapping.
4. `GET /filter` initially returns JSON containing the current `filter`.
5. Choose two emulator endpoints from the backend container data and build a
   narrow expression such as `icmp and host <destination-ip>`.
6. `PUT /filter` with `{"filter":"..."}` returns HTTP 200 and echoes the
   normalized active filter. If no interfaces are available, HTTP 503 is a test
   failure and the response text must be printed.
7. `GET /pcap` returns the current recording status. `PUT /pcap` with
   `{"enabled":true}` returns `enabled: true`; when the nonempty filter is
   active, `captureActive` must also be true.
8. Connect the packet WebSocket, generate a fixed number of matching packets,
   and wait with a bounded timeout for packet messages.

Each received WebSocket object must have `type: "packet"`. For generated ICMP
traffic, verify `sourceIp`, `destIp`, `ipProtocol: "icmp"`, `flowId`,
`packetId`, `packetRole`, `packetKind`, ICMP ID/sequence fields, and stable
source/destination container or node names. At least one request and its reply
must match the selected endpoints; unrelated host traffic cannot satisfy the
test.

Then verify recording and shutdown:

1. `GET /pcap` reports positive `packetCount`, `byteCount`, and `messageCount`,
   with nonempty `currentPcapFile` and `currentJsonFile` under `/data/pcap`.
2. The pcap and JSON message counts correspond, and both files describe the
   generated ICMP flow in event order.
3. `PUT /pcap` with `{"enabled":false}` returns `enabled: false`.
4. `PUT /filter` with `{"filter":""}` disables capture and ends the current
   batch. `GET /filter` then returns an empty value.
5. More matching traffic produces no new WebSocket packet event or recording
   count for that stopped batch.

Finally drive the same flow from the geographic frontend: enter the filter,
start capture, generate traffic, and verify the map shows the matching endpoints
and nonzero activity; stop capture and verify the UI stops updating. Reload the
page and repeat once to ensure there is no stale capture state.

Also exercise observer error responses without changing the running topology:

- Invalid filter syntax returns HTTP 400 with `invalid filter expression`.
- Malformed `/filter` JSON returns HTTP 400 with `invalid filter request`.
- `/pcap` without `enabled` returns HTTP 400 with `enabled is required`.
- Unsupported methods return HTTP 405 and an appropriate `Allow` header.
- CORS `OPTIONS` returns HTTP 204.

On any failure, print the functional checkpoint, method/path, expected and
actual status, and the short response body or WebSocket field mismatch directly
to the terminal. Do not save screenshots or request logs.

### Hosts records

Verify these names from all four running containers. Line order is not
significant.

| Name | Address |
| --- | --- |
| `emulator_api_server-e.map.seed.emu` | `172.30.0.10` |
| `internetmap_toplogy.map.seed.emu` | `172.30.0.11` |
| `internetmap_geo.map.seed.emu` | `172.30.0.12` |
| `emulator_api_server.map.seed.emu` | `10.151.0.16` |

### Map labels

The primary check is whether the Emulator API discovers the container from its
SeedEMU labels. Call `GET /api/v1/container` through both frontend proxies and
locate exactly one result whose parsed `meta.emulatorInfo.name` is
`emulator_api_server.map.seed.emu`.

For that result, verify the raw `Labels` and parsed `meta.emulatorInfo` agree:

- ASN is `151`.
- Node name is `emulator_api_server.map.seed.emu`.
- Role is `Host`.
- `net.0.name` is `net0` and `net.0.address` is `10.151.0.16`.
- The custom marker is present.

Compare the API result's container ID, runtime state, network addresses, and raw
labels with `docker inspect` for the running API container. This confirms that
the endpoint returned the intended live container rather than another object
with a matching name.

The topology UI, geographic UI, and observer do not have SeedEMU node labels
because they do not join an internal emulator network. Since
`GET /api/v1/container` filters out unlabeled containers, none of those three
containers may appear in its result.

