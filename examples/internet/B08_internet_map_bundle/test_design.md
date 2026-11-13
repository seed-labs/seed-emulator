# B08 Test Design

## 1. Container Checks

After the generated system has started, verify the following behavior for all
InternetMap bundle containers:

- Each expected bundle container is running normally and is not repeatedly
  restarting.
- Each container's live IPv4 addresses match the addresses assigned by the
  bundle.
- Bundle containers that share a bundle network can reach one another over that
  network.
- Every bundle container attached to an internal emulation network can reach
  the corresponding emulation-network gateway and nodes.
- Published host ports map to the intended bundle container ports.
- The following bundle records exist in `/etc/hosts` with their assigned
  addresses and can be resolved inside each applicable bundle container:

  ```text
  emulator_api_server.map.seed.emu
  emulator_api_server-e.map.seed.emu
  internetmap_toplogy.map.seed.emu
  emulator_api_server-e1.map.seed.emu
  internetmap_geo.map.seed.emu
  ```

The checks must inspect the running containers rather than relying only on the
generated Compose file.

## 2. `show_on_map` Label Checks

After the containers have started, inspect the labels of each bundle container
that is configured for display on the map. Verify that these labels exist:

```text
org.seedsecuritylabs.seedemu.meta.asn
org.seedsecuritylabs.seedemu.meta.nodename
org.seedsecuritylabs.seedemu.meta.role
org.seedsecuritylabs.seedemu.meta.net.0.name
org.seedsecuritylabs.seedemu.meta.net.0.address
org.seedsecuritylabs.seedemu.meta.custom
```

The value of `org.seedsecuritylabs.seedemu.meta.custom` must be exactly:

```text
custom
```

## 3. Topology Service Check

Send HTTP requests to the Topology Map page and its container and network APIs:

```text
http://127.0.0.1:8092/pro/map
http://127.0.0.1:8092/api/v1/container
http://127.0.0.1:8092/api/v1/network
```

The check passes when the page returns a successful nonempty response and both
APIs return successful JSON responses containing their result fields.

## 4. Traffic Observer Test

Use HTTP requests to verify that:

1. `http://127.0.0.1:8093/pro/map/3d` returns a successful nonempty response.
2. A capture filter can be set through the proxied Traffic Observer API and the
   response contains the requested filter.
3. The filter can be cleared and the response contains an empty filter.
