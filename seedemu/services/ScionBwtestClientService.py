from __future__ import annotations
from typing import Dict

from seedemu.core import Node, Server, Service


ScionBwtestClientTemplates: Dict[str, str] = {}

ScionBwtestClientTemplates['command_with_preference'] = """\
sleep {wait_time};
nohup scion-bwtestclient -s {server_addr}:{port} -sc {SC} -cs {CS} -preference {preference} >> /var/log/bwtestclient.log 2>&1 &
echo "bwtestclient started"
"""

ScionBwtestClientTemplates['command'] = """\
sleep {wait_time};
nohup scion-bwtestclient -s {server_addr}:{port} -sc {SC} -cs {CS} >> /var/log/bwtestclient.log 2>&1 &
echo "bwtestclient started"
"""


class ScionBwtestClient(Server):
    """!
    @brief SCION bandwidth test client.

    The output will be written to /var/log/bwtestclient.log
    """

    __port: int
    __server_addr: str
    __cs: str
    __sc: str
    __preference: str
    __wait_time: int

    def __init__(self):
        """!
        @brief ScionBwtestServer constructor.
        """
        super().__init__()
        self.__port = 40002
        self.__server_addr = "" # Server address in format ISD-AS,IP-Addr (e.g. 1-151,10.151.0.30)
        self.__cs = "3,1000,30,80kbps" # Client->Server test parameter default
        self.__sc = "3,1000,30,80kbps" # Server->Client test parameter default
        self.__preference = None
        self.__wait_time = 60 # Default time to wait before starting the client


    def setPort(self, port: int) -> ScionBwtestClient:
        """!
        @brief Set port the SCION bandwidth test server listens on.

        @param port
        @returns self, for chaining API calls.
        """
        self.__port = port

        return self
    
    def setServerAddr(self, server_addr: str) -> ScionBwtestClient:
        """!
        @brief Set the address of the SCION bandwidth test server.

        @param server_addr
        @returns self, for chaining API calls.
        """
        self.__server_addr = server_addr

        return self

    def setPreference(self, preference: str) -> ScionBwtestClient:
        """
        @brief Preference sorting order for paths. Comma-separated list of available sorting options: latency|bandwidth|hops|mtu

        @param preference
        @returns self, for chaining API calls.
        """
        self.__preference = preference

        return self
    
    def setCS(self, cs: str) -> ScionBwtestClient:
        """
        @brief set Client->Server test parameter (default "3,1000,30,80kbps")
        """
        self.__cs = cs

        return self

    def setSC(self, sc: str) -> ScionBwtestClient:
        """
        @brief Server->Client test parameter (default "3,1000,30,80kbps")
        """
        self.__sc = sc

        return self
    
    def setWaitTime(self, wait_time: int) -> ScionBwtestClient:
        """
        @brief Set the time to wait before starting the client
        """
        self.__wait_time = wait_time

        return self

        
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        if self.__preference:
            node.appendStartCommand(ScionBwtestClientTemplates['command_with_preference'].format(
                port=str(self.__port), server_addr=self.__server_addr, CS=self.__cs, SC=self.__sc, preference=self.__preference, wait_time=str(self.__wait_time)))
        else:
            node.appendStartCommand(ScionBwtestClientTemplates['command'].format(
                port=str(self.__port), server_addr=self.__server_addr, CS=self.__cs, SC=self.__sc, preference=self.__preference, wait_time=str(self.__wait_time)))
        node.appendClassName("ScionBwtestClientService")

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'SCION bandwidth test client object.\n'
        return out


class ScionBwtestClientService(Service):
    """!
    @brief SCION bandwidth test client service class.
    """

    def __init__(self):
        """!
        @brief ScionBwtestClientService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, False)

    def _createServer(self) -> Server:
        return ScionBwtestClient()

    def getName(self) -> str:
        return 'ScionBwtestClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ScionBwtestClientServiceLayer\n'
        return out
