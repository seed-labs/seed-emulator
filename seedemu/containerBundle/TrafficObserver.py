from .ContainerBundle import ContainerBundle

TRAFFIC_OBSERVER = "traffic_observer"
TRAFFIC_OBSERVER_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

class TrafficObserver(ContainerBundle):
    """!
    @brief Bundle for traffic views.

    The observer uses host networking and listens on the fixed
    ``TRAFFIC_OBSERVER_PORT`` ({}). Its control port is configured independently
    from the host-port pool. Only the API backend joins the first explicitly
    supplied internal network, using its first address; that attachment also
    adds the metadata labels used to display it on the map. Use unique suffixes,
    networks, and port pools for multiple instances.
    """

    def __init__(self, emulator, suffix=".map.seed"):
        """!
        @brief Create an Internet Map bundle.

        @param emulator emulator whose topology will be visualized.
        @param suffix suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)

        self._createContainer(TRAFFIC_OBSERVER, suffix)
        self._required_port_count = 1
        self._required_internal_address_count = 0
        self._interface_count = 0

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
                    "./traffic-observer-service/pcap:/data/pcap",
                ],
            }
        )
        traffic_observer._service_ports = [traffic_observer_port]

    def set_interface_count(self, interface_count: int):
        """!
        @brief Set a standard for the number of networks retrieved to avoid not obtaining all the networks in the emulator system.
        """
        self._interface_count = interface_count
