from __future__ import annotations
from seedemu.core import AutonomousSystem, Emulator, Network, Node, Service, Server
from .traffic_receiver import TrafficReceiver
from typing import List, Union


class TrafficGeneratorServer(Server):
    def __init__(self, generator: TrafficGenerator):
        self.generator = generator
        super().__init__()

    def install(self, node: Node):
        self.generator.install_softwares(node)
        node.appendClassName("TrafficGenerator")
        node.setDomainName(self.generator.getName())

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGenerator server object.\n'

        return out

class TrafficGenerator(Service):
    def __init__(self, name=None):
        super().__init__()

        self.name = name or self.__class__.__name__
        self.targets = {
            "asns": [],
            "hosts": []
        }
        self.node = None
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return TrafficGeneratorServer(self)

    def render(self, emulator: Emulator):
        super().render(emulator)
        base_layer = emulator.getLayer('Base')
        target_nodes = []
        for asn in self.targets['asns']:
            target = base_layer.getAutonomousSystem(asn)
            as_nets = target.getNetworks()
            for as_net in as_nets:
                target_nodes.append(str(target.getNetwork(as_net).getPrefix()))
        for host in self.targets['hosts']:
            target_nodes.append(host)
        print()
        self.node.setFile('/root/traffic-targets', "\n".join(target_nodes))

    def install_softwares(self, node: Node):
        self.node = node

    def addTargets(self, asns: List[AutonomousSystem] = [], hosts: List[str] = []):
        self.targets["asns"].extend(asns)
        self.targets["hosts"].extend(hosts)

    def getName(self) -> str:
        return self.name
  
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGeneratorLayer\n'

        return out
