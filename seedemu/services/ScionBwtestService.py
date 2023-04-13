from __future__ import annotations
from typing import Dict

from seedemu.core import Node, Server, Service


ScionBwtestServerTemplates: Dict[str, str] = {}

ScionBwtestServerTemplates['command'] = """\
until pgrep -xf "scion-bwtestserver --listen=:{port}" > /dev/null 2>&1;
do
    sleep 5;
    nohup scion-bwtestserver --listen=:{port} >> /var/log/bwtestserver.log 2>&1 &
done
echo "bwtestserver started"
"""


class ScionBwtestServer(Server):
    """!
    @brief SCION bandwidth test server.
    """

    __port: int

    def __init__(self):
        """!
        @brief ScionBwtestServer constructor.
        """
        super().__init__()
        self.__port = 40002

    def setPort(self, port: int) -> ScionBwtestServer:
        """!
        @brief Set port the SCION bandwidth test server listens on.

        @param port
        @returns self, for chaining API calls.
        """
        self.__port = port

        return self

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendStartCommand(ScionBwtestServerTemplates['command'].format(
            port=str(self.__port)))
        node.appendClassName("ScionBwtestService")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'SCION bandwidth test server object.\n'
        return out


class ScionBwtestService(Service):
    """!
    @brief SCION bandwidth test server service class.
    """

    def __init__(self):
        """!
        @brief ScionBwtestService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, False)

    def _createServer(self) -> Server:
        return ScionBwtestServer()

    def getName(self) -> str:
        return 'ScionBwtestService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ScionBwtestServiceLayer\n'
        return out
