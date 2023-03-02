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

class ScionBwtestClientServer(Server):
    """!
    @brief The ScionBwtestClientServer class.
    """

    __port: int
    __dst_isd: int
    __dst_asn: int
    __dst_ip: str
    __duration: int
    __pkt_size: int
    __pkt_cnt: str
    __bandwidth: str

    def __init__(self):
        """!
        @brief ScionBwtestClientServer constructor.
        """
        self.__port = 40002
        self.__duration = 3
        self.__pkt_size = 1000
        self.__pkt_cnt = '?'
        self.__bandwidth = '80kbps'

    def setPort(self, port: int) -> ScionBwtestClientServer:
        """!
        @brief Set port the SCION bandwidth test server that should be connected to listens on.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self
        
    def setDuration(self, duration: int):
        """!
        @brief Set duration over which the bandwidth should be tested.

        @param duration duration.

        @returns self, for chaining API calls.
        """
        self.__duration = duration
        
        return self
        
    def setPacketSize(self, pkt_size: int):
        """!
        @brief Set the packet size which is used in bandwidth tests.

        @param pkt_size packet size.

        @returns self, for chaining API calls.
        """
        self.__pkt_size = pkt_size
        
        return self
        
    def setBandwidth(self, bandwidth: str):
        """!
        @brief Set the bandwidth that should be attempted during the bandwidth test.

        @param bandwidth bandwidth.

        @returns self, for chaining API calls.
        """
        self.__bandwidth = bandwidth
        
        return self
        
    def setAS(self, as_addr: IA|Tuple[int, int]):
        """!
        @brief Set the AS of the server that should be connected to.

        @param as AS the client should bind to (ISD and ASN).

        @returns self, for chaining API calls.
        """
        as_addr = IA(*as_addr)
        self.__dst_isd = as_addr.isd
        self.__dst_asn = as_addr.asn
        
        return self
        
    def setIP(self, addr: str):
        """!
        @brief Set the IP address the server is running on that should be connected to.

        @param addr IP address.

        @returns self, for chaining API calls.
        """
        self.__dst_ip = addr
        
        return self
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendStartCommand(ScionBwtestServerTemplates['wait_for_scion'].format(command= \
                                'scion-bwtestclient -s '+str(self.__dst_isd)+'-'+str(self.__dst_asn)+','+self.__dst_ip+':'+str(self.__port) \
                                +' -cs '+str(self.__duration)+','+str(self.__pkt_size)+','+self.__pkt_cnt+','+self.__bandwidth))
        node.appendClassName("ScionBwtestClientService")
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'SCION bandwidth test client server object.\n'

        return out

class ScionBwtestClientService(Service):
    """!
    @brief The ScionBwtestClientService class.
    """

    def __init__(self):
        """!
        @brief ScionBwtestClientService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Scion', False, False)

    def _createServer(self) -> Server:
        return ScionBwtestClientServer()

    def install(self, vnode: str, bw_server: IA|Tuple[int, int], ip_addr: str):
        """!
        @brief Install the service on a node identified by a given name with setting the bandwidth test server's address.

        @param bw_server AS address of the bandwidth server (ISD and ASN).
        @param ip_addr IP address of the bandwidth server. 

        @returns self, for chaining API calls.
        """
        server = super().install(vnode)
        server.setAS(bw_server)
        server.setIP(ip_addr)
        return server

    def getName(self) -> str:
        return 'ScionBwtestClientService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ScionBwtestClientServiceLayer\n'

        return out
