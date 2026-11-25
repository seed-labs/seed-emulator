from .ContainerBundle import ContainerBundle, PreparedContainer

TRAFFIC_OBSERVER_PORT = 19090
TRAFFIC_OBSERVER = "traffic_observer"
TRAFFIC_OBSERVER_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

class SystemBundle(ContainerBundle):
    """!
    @brief Bundle for traffic views.

    The observer uses host networking and listens on the fixed
    ``TRAFFIC_OBSERVER_PORT`` ({}). Its control port is configured independently
    from the host-port pool. Only the API backend joins the first explicitly
    supplied internal network, using its first address; that attachment also
    adds the metadata labels used to display it on the map. Use unique suffixes,
    networks, and port pools for multiple instances.
    """

    def __init__(self, emulator, suffix=".system.seed", ports=[]):
        """!
        @brief Create an Internet Map bundle.

        @param emulator emulator whose topology will be visualized.
        @param suffix suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)
        traffic_observer = PreparedContainer(name=TRAFFIC_OBSERVER, suffix=suffix, emulator=emulator)
        self._containers.update({TRAFFIC_OBSERVER: traffic_observer})
        self._shared_containers.update({TRAFFIC_OBSERVER: traffic_observer})
        self._required_port_count = 1
        self._required_internal_address_count = 0
        self._interface_count = 0
        self._ports = [TRAFFIC_OBSERVER_PORT]
        self._interface_count = emulator.getNodeCount()

    def configure(self) -> None:
        """!
        @brief Validate ports and configure all InternetMap services.

        @raises AssertionError when fewer than one host port is configured.
        """
        super().configure()

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