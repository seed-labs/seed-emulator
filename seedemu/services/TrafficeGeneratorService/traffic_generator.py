from __future__ import annotations
from seedemu.core import AutonomousSystem, Emulator, Network, Node, Service, Server
from .traffic_receiver import TrafficReceiver
from typing import List, Union


class TrafficGenerator(Server):
    def __init__(self, base_layer, name=None, targets=None):
        super().__init__()
        self.name = name or  self.__class__.__name__
        self.targets = {
            "asns": [],
            "hosts": []
        }
        if targets:
            self.targets = targets
        self.base_layer = base_layer

    def addTargets(self, asns: List[AutonomousSystem] = [], hosts: List[str] = []):
        self.targets["asns"].extend(asns)
        self.targets["hosts"].extend(hosts)

    def install(self, node: Node):
        node.appendClassName("TrafficGenerator")
        node.addHostName(self.name)
        target_nodes = []
        for asn in self.targets['asns']:
            target = self.base_layer.getAutonomousSystem(asn)
            as_nets = target.getNetworks()
            for as_net in as_nets:
                target_nodes.append(str(target.getNetwork(as_net).getPrefix()))
        for host in self.targets['hosts']:
            target_nodes.append(host)
        node.setFile('/root/traffic-targets', "\n".join(target_nodes))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGenerator object.\n'

        return out


class TrafficService(Service):
    def __init__(self):
        super().__init__()
        self.servers = {}
        self.addDependency('Base', False, False)

    def addServer(self, name, server: Server):
        self.servers[name] = server
        return self
    
    def install(self):
        for vnode, server in self.servers.items():
            self._pending_targets[vnode] = server

    def getName(self) -> str:
        return self.__class__.__name__
  
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGeneratorLayer\n'

        return out
