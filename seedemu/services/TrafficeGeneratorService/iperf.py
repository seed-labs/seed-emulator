from __future__ import annotations
from seedemu.core import Node
from .traffic_receiver import TrafficReceiver
from .traffic_generator import TrafficGenerator


class IperfReceiver(TrafficReceiver):
    def install_softwares(self, node: Node):
        super().install_softwares(node)
        node.addSoftware('iperf3')
        node.appendStartCommand('iperf3 -s -D')

class IperfGenerator(TrafficGenerator):
    def install_softwares(self, node: Node):
        super().install_softwares(node)
        node.addSoftware('iperf3')
