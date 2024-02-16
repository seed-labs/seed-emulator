from __future__ import annotations
from seedemu.core import Node, Service, Server


class TrafficReceiverServer(Server):
    """!
    @brief The TrafficReceiverServer class.
    """
    def __init__(self, receiver: TrafficReceiver):
        """!
        @brief TrafficReceiverServer constructor.
        """
        super().__init__()
        self.receiver = receiver

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        self.receiver.install_softwares(node)
        node.appendClassName("TrafficReceiver")
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Traffic receiver server object.\n'

        return out

class TrafficReceiver(Service):
    """!
    @brief The TrafficReceiver class.
    """

    def __init__(self, name=None):
        """!
        @brief TrafficReceiver constructor.
        """
        super().__init__()
        self.node = None
        self.name = name or  self.__class__.__name__
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return TrafficReceiverServer(self)

    def install_softwares(self, node: Node):
        self.node = node
    
    def getNodeName(self) -> str:
        print(type(self.node))
        print(self.node)
        return f"{self.node.getScope()}-{self.node.getName()}" if self.node else ""

    def getName(self) -> str:
        return self.name

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficReceiverLayer\n'

        return out
