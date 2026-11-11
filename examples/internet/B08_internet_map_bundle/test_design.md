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

Open the Topology Map page exposed by `internetmap_toplogy`:

```text
http://127.0.0.1:8092/pro/map
```

Verify that the page loads successfully and that the topology is rendered with
the expected nodes and networks.

## 4. Traffic Observer Test

Traffic Observer packet capture depends on the host eBPF subsystem. Even a
minor host-kernel version change may affect this function, so the runtime test
must exercise real packet capture rather than checking only whether the
container or control service is running.

Use the Traffic Observer API to:

1. Discover the available capture interfaces.
2. Set a narrow packet-capture filter and start capture.
3. Generate matching traffic from an emulation container.
4. Receive captured packet data through the packet stream.
5. Verify that at least one captured packet matches the configured filter and
   the generated traffic endpoints.
6. Stop capture and clear the filter during cleanup, whether the test succeeds
   or fails.
