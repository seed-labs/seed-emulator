from __future__ import annotations
from seedemu.core import Node
import os
from .traffic_generator import TrafficGenerator


class ScapyGenerator(TrafficGenerator):
    def get_file_content(self, filename):
        """!
        @brief Get the content of a file
        @param filename the file name
        @return the content of the file
        """
        with open(filename, "r") as file:
            return file.read()

    def install_softwares(self, node: Node):
        """
        @brief Install necessary softwares.
        """
        node.addSoftware("python3")
        node.addSoftware("python3-pip")
        node.addBuildCommand("pip3 install scapy==2.5.0")
        scapy_generator_file = (
            os.path.dirname(os.path.realpath(__file__)) + "/scapy_script.py"
        )
        node.setFile(
            "/root/traffic_generator.py", self.get_file_content(scapy_generator_file)
        )
        node.appendStartCommand("chmod +x /root/traffic_generator.py")
        arguments = f"-t {self.duration} -l {self.log_file}"
        self.start_scripts.append(f"/root/traffic_generator.py {arguments} &")
