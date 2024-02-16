from __future__ import annotations
from seedemu.core import AutonomousSystem, Network, Node, Service, Server
from typing import List


class TrafficGeneratorServer(Server):
    def __init__(self, generator: TrafficGenerator):
        self.generator = generator
        super().__init__()

    def install(self, node: Node):
        self.generator.install_softwares(node)
        node.appendClassName("TrafficGenerator")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGenerator server object.\n'

        return out

class TrafficGenerator(Service):
    def __init__(self, name=None, targets: List[Service] | List[Network] | List[AutonomousSystem] = []):
        self.node = None
        self.name = name or self.__class__.__name__
        self.targets = targets
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return TrafficGeneratorServer(self)

    def install_softwares(self, node: Node):
        self.node = node
        target_nodes = []
        for target in self.targets:
            if isinstance(target, Service):
                target_nodes.append(target.getNodeName())
            elif isinstance(target, Network):
                target_nodes.append(str(target.getPrefix()))
            elif isinstance(target, AutonomousSystem):
                as_nets = target.getNetworks()
                for as_net in as_nets:
                    target_nodes.append(str(target.getNetwork(as_net).getPrefix()))
        node.setFile('/root/traffic-targets', "\n".join(target_nodes))

    def addTargets(self, targets: List[Service] | List[Network] | List[AutonomousSystem]):
        self.targets.extend(targets)

    def getNodeName(self) -> str:
        print(type(self.node))
        print(self.node)
        return f"{self.node.getScope()}-{self.node.getName()}" if self.node else ""

    def getName(self) -> str:
        return self.name
  
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGeneratorLayer\n'

        return out
