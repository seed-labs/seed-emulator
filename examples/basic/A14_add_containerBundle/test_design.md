# A14 runtime test design

## Expected containers

| Container | Expected connectivity | Expected service |
| --- | --- | --- |
| `demo-app.demo.seed` | `172.31.0.10`, `10.151.0.16`, `10.152.0.16` | Entrypoint wrapper followed by `sleep infinity` |
| `demo-helper.demo.seed` | `172.31.0.11` | Entrypoint wrapper followed by `sleep infinity` |

## Runtime checks

### Container state and startup

- Both containers are running and are not restarting.
- Both use `/new-entrypoint.sh`, and the expected long-running `sleep infinity`
  process exists.
- The app contains executable `/usr/local/bin/demo-message.sh`; executing it
  prints `ContainerBundle demo is running`.
- The app environment contains `DEMO_SUFFIX=.demo.seed`.
- Startup logs contain no route, hosts-file, entrypoint, or permission error.

### Interfaces and routes

- The app has live addresses `172.31.0.10`, `10.151.0.16`, and `10.152.0.16`.
- The helper has `172.31.0.11` and has no AS151/AS152 address.
- The app default route uses `10.151.0.254`.
- The app can ping both emulator gateways, `10.151.0.254` and `10.152.0.254`.
- The app and helper can ping each other through `172.31.0.10/11`.

### Port behavior

- Docker reports host TCP 8090 mapped to app TCP 8080.
- The helper has no published port.
- The current demo starts no service on app port 8080. Verify that no process is
  listening there and that a bounded connection to host port 8090 fails rather
  than hangs. If the example later adds an HTTP service, replace this assertion
  with a successful request.

### Hosts records

Verify the following names from both running containers. Line order in
`/etc/hosts` is not significant.

| Name | Address |
| --- | --- |
| `demo-app-e.demo.seed` | `172.31.0.10` |
| `demo-helper-e.demo.seed` | `172.31.0.11` |
| `demo-app-demo_bundle_network` | `172.31.0.10` |
| `demo-helper-demo_bundle_network` | `172.31.0.11` |
| `demo-app.demo.seed` | `10.151.0.16` |
| `demo-app-net_151_net0` | `10.151.0.16` |
| `demo-app-net_152_net0` | `10.152.0.16` |

### Map labels

Inspect the running app container labels:

- ASN is `152`.
- Node name is `demo-app.demo.seed`.
- Role is `Host`.
- `net.0.name` is `net0` and `net.0.address` is `10.152.0.16`.
- The custom marker is present.

The AS152 values are expected because the second internal-network attachment
replaces the map labels from the first. The helper must not have these node
labels.

