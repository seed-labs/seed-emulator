from __future__ import annotations
from seedemu.core import Node, Server
from typing import List


class TrafficGenerator(Server):
    startup_script = """
echo "Check if targets are reachable";
while read client; do
    while true; do ping -c1 $client > /dev/null && break; done;
done < /root/traffic-targets
echo "Starting traffic generator"
while read client; do
    {cmdline} &
done < /root/traffic-targets
"""

    def __init__(
        self,
        name: str = None,
        log_file: str = "/root/traffic_generator.log",
        duration: int = 300,
        rate: int = 5000,
        protocol: str = "TCP",
        auto_start: bool = True,
        extra_options: str = ""
    ):
        """!
        @brief TrafficGenerator constructor.
        @param name name of the generator.
        @param log_file log file.
        @param duration duration of traffic generation process.
        @param rate rate in bits/sec (0 for unlimited).
        @param protocol protocol.
        @param auto_start start the traffic generator script automatically.
        @param extra_options extra options.
        """
        super().__init__()
        self.name = name or self.__class__.__name__
        self.log_file = log_file
        self.duration = duration
        self.rate = rate
        self.protocol = protocol
        self.extra_options = extra_options
        self.auto_start = auto_start
        self.receiver_hosts = []
        self.start_scripts = []
        self.traffic_generators = []

    def addReceivers(self, hosts: List[str] = []):
        """!
        @brief Add traffic receiver hosts.
        @param hosts list of receiver hosts.
        """
        self.receiver_hosts.extend(hosts)

    def install_softwares(self, node: Node):
        """!
        @brief Install necessary softwares.
        """
        raise NotImplementedError

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addHostName(self.name)
        node.appendClassName("TrafficGenerator")
        node.setFile("/root/traffic-targets", "\n".join(list(set(self.receiver_hosts))))
        
        for server in self.traffic_generators:
            server.install_softwares(node)

        if self.auto_start:
            self.start(node)

    def start(self, node: Node):
        """!
        @brief Start the scripts automatically on boot up.
        """
        for server in self.traffic_generators:
            for script in server.start_scripts:
                node.appendStartCommand(script)

    def print(self, indent: int) -> str:
        out = " " * indent
        out += "TrafficGenerator object.\n"

        return out

    def extend(self, server: TrafficGenerator):
        """!
        @brief Extend the traffic generator.
        """
        self.traffic_generators.append(server)
        return self
