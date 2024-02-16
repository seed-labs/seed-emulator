from __future__ import annotations
from seedemu.core import Node
import os
from .traffic_generator import TrafficGenerator

class ScapyGenerator(TrafficGenerator):
    def get_file_content(self, filename):
        with open(filename, 'r') as file:
            return file.read()

    def install_softwares(self, node: Node):
        super().install_softwares(node)
        node.addSoftware('python3')
        node.addSoftware('python3-pip')
        node.addBuildCommand('pip3 install scapy==2.5.0')
        scapy_generator_file = os.path.dirname(os.path.realpath(__file__)) + '/scapy_generator.py'
        node.setFile('/root/traffic_generator.py', self.get_file_content(scapy_generator_file))
        node.appendStartCommand('chmod +x /root/traffic_generator.py')
        node.appendStartCommand('/root/traffic_generator.py > /root/traffic.log')
