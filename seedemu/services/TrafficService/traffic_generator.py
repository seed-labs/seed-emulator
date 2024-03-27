from __future__ import annotations
from seedemu.core import  Node, Server
from typing import List


class TrafficGenerator(Server):
    def __init__(self, name=None):
        super().__init__()
        self.name = name or  self.__class__.__name__
        self.receiver_hosts = []

    def addReceivers(self, hosts: List[str] = []):
        self.receiver_hosts.extend(hosts)

    def install(self, node: Node):
        node.addHostName(self.name)
        node.appendClassName("TrafficGenerator")
        node.setFile('/root/traffic-targets', "\n".join(self.receiver_hosts))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGenerator object.\n'

        return out
