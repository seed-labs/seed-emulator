from . import IperfReceiver, IperfGenerator, DITGGenerator, DITGReceiver, ScapyGenerator
from seedemu.core import Node

class HybridTrafficReceiver(IperfReceiver, DITGReceiver):
    def install_softwares(self, node: Node):
        super().install_softwares(node)

class HybridTrafficGenerator(IperfGenerator, DITGGenerator, ScapyGenerator):
    def install_softwares(self, node: Node):
        super().install_softwares(node)
