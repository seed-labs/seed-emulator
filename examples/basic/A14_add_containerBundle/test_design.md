# A14 Test Design

## 1. Container Checks

After the generated system has started, verify the following behavior for all
ContainerBundle containers:

- Each expected bundle container is running normally and is not repeatedly
  restarting.
- Each container's live IPv4 addresses match the addresses assigned by the
  bundle.
- The bundle containers can reach one another over their shared bundle network.
- Every bundle container attached to an internal emulation network can reach
  the corresponding emulation-network gateway and nodes.
- Published host ports map to the intended bundle container ports.
- Every record added by the bundle is present in `/etc/hosts` with the correct
  address and can be resolved inside each applicable bundle container.

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
