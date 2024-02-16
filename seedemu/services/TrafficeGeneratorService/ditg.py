from __future__ import annotations
from seedemu.core import Node
from .traffic_receiver import TrafficReceiver
from .traffic_generator import TrafficGenerator


class DITGReceiver(TrafficReceiver):
    def install_softwares(self, node: Node):
        super().install_softwares(node)
        node.addSoftware('d-itg')
        node.appendStartCommand('ITGRecv')

class DITGGenerator(TrafficGenerator):
    def install_softwares(self, node: Node):
        super().install_softwares(node)
        node.addSoftware('d-itg')


# Uses
# receiver1 = DITGReceiver(name='ditg_receiver_1')
# receiver2 = DITGReceiver(name='ditg_receiver_2')
# generator1 = DITGGenerator(name='g1', [receiver1.name, receiver2.name])
# generator2 = DITGGenerator(name='g2', targets=[as1.name, ast.name])
# generator3 = DITGGenerator(name='g3', targets=base.allNetworks())
# generator4 = DITGGenerator(name='g4', targets=base.allNodes())
