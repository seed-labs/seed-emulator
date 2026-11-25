# SystemBundle design

[`SystemBundle.py`](../../seedemu/containerBundle/SystemBundle.py) contains
compiler-managed services that support the emulation as a whole. `Docker`
creates and compiles it automatically; callers do not add it with
`addContainerBundle()`. The bundle is separate from user-facing bundles such as
[`InternetMap`](internet_map_bundle.md). Its current service is
`traffic_observer` (`traffic_observer.system.seed`).

During Docker compilation the compiler inserts the system bundle before
user-added bundles, then runs the same configure/install lifecycle for both:

```python
# Docker._doCompile(), simplified
self.__containerBundles.insert(0, SystemBundle(emulator))
for bundle in self.__containerBundles:
    services, networks = self._compileContainerBundle(bundle)
```

This keeps compiler-managed services out of `InternetMap`'s container list while
letting the compiler emit them in the same Compose project.

## Traffic observer service

The observer runs with Docker host networking and the host PID namespace. It
also runs privileged, mounts the host debug and BPF filesystems, and mounts the
Docker socket read-only. With `network_mode: host`, the observer shares the
Docker host's network namespace. It has no separate container IP and does not
use a Compose `ports` mapping. Its HTTP control service listens on all host
interfaces at the configured port.

The default port is `19090`, defined by `TRAFFIC_OBSERVER_PORT` in
`SystemBundle.py`. `SystemBundle` uses the first port in its host-port list for
the observer. Set a custom port with the inherited `setPorts()` API:

```python
system_bundle = SystemBundle(emulator)
system_bundle.setPorts([19100])
```

The configuration reads the port from `self._ports[0]`, passes it to
`TRAFFIC_CONTROL_ADDR`, and records it in `_service_ports`:

The relevant configuration is equivalent to:

```python
traffic_observer = self._containers[TRAFFIC_OBSERVER]
traffic_observer_port = self._ports[0]
traffic_observer.updateServiceConfig(
    {
        "image": TRAFFIC_OBSERVER_IMAGE,
        "privileged": True,
        "pid": "host",
        "network_mode": "host",
        "environment": {
            "TRAFFIC_CONTROL_ADDR": f":{traffic_observer_port}",
            "TRAFFIC_LOG_TIMEZONE": "Asia/Shanghai",
            "TRAFFIC_EXPECTED_INTERFACE_COUNT": int(self._interface_count)
        },
        "volumes": [
            "/sys/kernel/debug:/sys/kernel/debug",
            "/sys/fs/bpf:/sys/fs/bpf",
            "/var/run/docker.sock:/var/run/docker.sock:ro",
        ],
    }
)
traffic_observer._service_ports = [traffic_observer_port]
```

The same port is used by `InternetMap` when it generates the geographic UI
proxy target. Recompile after setting the port so the generated Compose
configuration and proxy target are refreshed. Any other client configuration
and host firewall rules must use that port too.

## Access from other containers

An external container on a Docker bridge can reach the host-network observer
through the Docker host gateway, provided host routing and firewall rules allow
the connection. `InternetMap`'s geographic UI does this by mapping
`host.docker.internal` to Docker's `host-gateway` and proxying
`/traffic-observer/` to `host.docker.internal:19090` by default. If a custom
port is set through `setPorts()`, the proxy target is generated from the system bundle's configured
service port. The corresponding Compose/Nginx setup is:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

```nginx
upstream traffic_observer {
    server host.docker.internal:19100;
}
```

Emulator node containers do not currently have a built-in TrafficObserver
integration or a predefined `host.docker.internal` alias. They can still make a
direct request to the Docker gateway address of the Docker network attached to
that container, using the observer port. For example, if the relevant Compose
network has gateway `172.30.0.1` and the default observer port is in use, the
endpoint is `http://172.30.0.1:19090/`. Set the gateway to the host-side gateway
of a Docker bridge attached to that emulator container. Do not assume the
emulated routing default points to Docker's host gateway; inspect the Compose
network's gateway or the container's interface and route configuration. For
example, after identifying the correct gateway:

```sh
DOCKER_GATEWAY=172.30.0.1
curl "http://${DOCKER_GATEWAY}:19090/"
```

Use the gateway for the container's Docker network, not an emulated network's
router address. The Docker host must accept traffic to that address and port.

The observer's use of host networking means its many visible interface
addresses are host addresses. Clients should select the reachable host-gateway
address for their own Docker network rather than infer an observer-specific
container IP.

## Runtime requirements

The observer image requires Linux host kernel facilities and the configured
debugfs, BPF, and Docker socket mounts. Host networking exposes the listening
port on the Docker host's network namespace; external reachability still depends
on host routing and firewall configuration. The service is not part of the
InternetMap bundle lifecycle, although InternetMap's geographic UI proxies to
it when both are compiled together.
