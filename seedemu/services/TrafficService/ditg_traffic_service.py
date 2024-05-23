from __future__ import annotations
from seedemu.core import Node
from .traffic_receiver import TrafficReceiver
from .traffic_generator import TrafficGenerator


class DITGReceiver(TrafficReceiver):

    def install_softwares(self, node: Node):
        """!
        @brief Install necessary softwares.
        """
        node.addSoftware("d-itg")
        node.appendStartCommand(f"ITGRecv  -l {self.log_file} &")


class DITGGenerator(TrafficGenerator):

    def install_softwares(self, node: Node):
        """!
        @brief Install necessary softwares.
        """
        node.addSoftware("d-itg")
        cmdline = (
            "ITGSend -a $client -T "
            + self.protocol
            + " -t "
            + str(self.duration * 1000)
            + " -l "
            + self.log_file
            + " -C "
            + str(self.rate)
            + " "
            + self.extra_options
        )
        node.setFile(
            "/root/traffic_generator_ditg.sh",
            self.startup_script.format(cmdline=cmdline),
        )
        node.appendStartCommand("chmod +x /root/traffic_generator_ditg.sh")
        self.start_scripts.append("/root/traffic_generator_ditg.sh &")
