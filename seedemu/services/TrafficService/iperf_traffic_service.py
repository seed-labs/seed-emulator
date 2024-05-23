from __future__ import annotations
from seedemu.core import Node
from .traffic_receiver import TrafficReceiver
from .traffic_generator import TrafficGenerator


class IperfReceiver(TrafficReceiver):

    def install_softwares(self, node: Node):
        """!
        @brief Install necessary softwares.
        """
        node.addSoftware("iperf3")
        node.appendStartCommand("iperf3 -s -D --logfile " + self.log_file)


class IperfGenerator(TrafficGenerator):

    def install_softwares(self, node: Node):
        """!
        @brief Install necessary softwares.
        """
        node.addSoftware("iperf3")

        cmdline = f"iperf3 -c $client --logfile {self.log_file} -t {self.duration} -b {self.rate} "
        if self.protocol == "UDP":
            cmdline += "-u "
        cmdline += self.extra_options

        node.setFile(
            "/root/traffic_generator_iperf3.sh",
            self.startup_script.format(cmdline=cmdline),
        )
        node.appendStartCommand("chmod +x /root/traffic_generator_iperf3.sh")
        self.start_scripts.append("/root/traffic_generator_iperf3.sh &")

