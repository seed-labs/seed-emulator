from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.ScionAutonomousSystem import IA
from typing import Dict

ScionBwtestServerTemplates: Dict[str, str] = {}

ScionBwtestServerTemplates['wait_for_scion'] = '''\
bash -c 'until [ -e /run/shm/dispatcher/default.sock ]; do sleep 1; done; until [ -e /var/log/sciond.log ]; do sleep 1; done; {command}; if [ $? -ne 0 ]; then echo "Retrying in 10 sec..."; sleep 10; {command}; fi;'\
'''

class ScionBwtestServerServer(Server):
    """!
    @brief The ScionBwtestServerServer class.
    """

    __port: int

    def __init__(self):
        """!
        @brief ScionBwtestServerServer constructor.
        """
        self.__port = 40002
        

    def setPort(self, port: int) -> ScionBwtestServerServer:
        """!
        @brief Set port the SCION bandwidth test server listens on.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendStartCommand(ScionBwtestServerTemplates['wait_for_scion'].format(command='scion-bwtestserver --listen=:' + str(self.__port)))
        node.appendClassName("ScionBwtestServerService")
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'SCION bandwidth test server server object.\n'

        return out

class ScionBwtestServerService(Service):
    """!
    @brief The ScionBwtestServerService class.
    """

    def __init__(self):
        """!
        @brief ScionBwtestServerService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, False)

    def _createServer(self) -> Server:
        return ScionBwtestServerServer()

    def getName(self) -> str:
        return 'ScionBwtestServerService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ScionBwtestServerServiceLayer\n'

        return out
