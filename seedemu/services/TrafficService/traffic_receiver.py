from __future__ import annotations
from seedemu.core import Node, Server


class TrafficReceiver(Server):
    """!
    @brief The TrafficReceiver class.
    """

    def __init__(self, name: str = None, log_file: str = "/root/traffic_receiver.log"):
        """!
        @brief TrafficReceiver constructor.
        @param name name of the receiver.
        @param log_file log file.
        """
        super().__init__()
        self.name = name or self.__class__.__name__
        self.log_file = log_file

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("TrafficReceiver")
        node.addHostName(self.name)

    def print(self, indent: int) -> str:
        out = " " * indent
        out += "Traffic receiver server object.\n"

        return out
