from re import S
from .Layer import Layer
from seedsim.core import Node, Printable, Simulator
from seedsim.core.enums import NodeRole
from typing import Dict, List, Set, Tuple

class Server(Printable):
    """!
    @brief Server class.

    The Server class is the handler for installed services.
    """

    def install(self, node: Node):
        """!
        @brief Install the server on node.

        @param node node.
        """
        raise NotImplementedError('install not implemented')

class Service(Layer):
    """!
    @brief Service base class.

    The base class for all Services.
    """

    __ip_targets: Set[Tuple[Server, str, int]]
    __name_targets: Set[Tuple[Server, str, int]]
    
    __targets: Set[Tuple[Server, Node]]

    def __init__(self):
        super().__init__()
        self.__ip_targets = set()
        self.__name_targets = set()
        self.__targets = set()

    def _createServer(self) -> Server:
        """!
        @brief Create a new server.
        """
        raise NotImplementedError('_createServer not implemented')

    def _doInstall(self, node: Node, server: Server):
        """!
        @brief install the server on node. This can be overrided by service
        implementations.

        @param node node.
        @param server server.
        """
        server.install(node)

    def _doConfigure(self, node: Node, server: Server):
        """!
        @brief configure the node. Some services may need to by configure before
        rendered.

        This is currently used by the DNS layer to configure NS and gules
        records before the actuall installation.
        
        @param node node
        @param server server
        """
        return

    def __configureServer(self, server: Server, node: Node):
        """!
        @brief Configure the service on given node.

        @param node node to configure the service on.

        @throws AssertionError if node is not host node.
        """
        assert node.getRole() == NodeRole.Host, 'node as{}/{} is not a host node'.format(node.getAsn(), node.getName())
        servicesdb: Dict = node.getAttribute('services', {})

        for (name, service_info) in servicesdb.items():
            service: Service = service_info['__self']
            assert name not in self.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())
            assert self.getName() not in service.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())

        m_name = self.getName()
        if m_name not in servicesdb:
            servicesdb[m_name] = {
                '__self': self
            }

        self._doConfigure(node, server)
        self.__targets.add((server, node))

    def configure(self, simulator: Simulator):
        reg = simulator.getRegistry()

        for (server, address, asn) in self.__ip_targets:
            hit = False
            for (scope, type, name), obj in reg.getAll().items():
                if type != 'hnode': continue

                node: Node = obj
                if asn != None and str(asn) != scope: continue
                for iface in node.getInterfaces():
                    if str(iface.getAddress()) == address:
                        hit = True
                        self.__configureServer(server, node)
                        self._log('ip-conf: configure on as{}/{} ({}).'.format(scope, name, address))
            
            assert hit, 'no node with IP address {}'.format(address)

        for (server, name, asn) in self.__name_targets:
            hit = False
            for (scope, type, _name), node in reg.getAll().items():
                if type != 'hnode' or scope != str(asn) or _name != name: continue
                hit = True
                self.__configureServer(server, node)
                self._log('conf: configure on as{}/{}.'.format(scope, name))
                break
            
            assert hit, 'no node with IP name {} in as{}'.format(name, scope)
    
    def render(self, simulator: Simulator):
        for (server, node) in self.__targets:
            self._doInstall(node, server)
        
    def getConflicts(self) -> List[str]:
        """!
        @brief Get a list of conflicting services.

        Override to change.

        @return list of service names.
        """
        return []

    def getTargets(self) -> Set[Tuple[Server, Node]]:
        """!
        @brief Get nodes and the server object associated with them. Note this
        only work after the layer is configured.
        """
        return self.__targets

    def installByIp(self, address: str, asn: int = None) -> Server:
        """!
        @brief Install to node by IP address.

        @param address IP address
        @param asn (optional) ASN to limit the scope of IP address

        @returns server instance.
        """
        for (s, addr, _asn) in self.__ip_targets:
            if addr == address and _asn == asn: return s

        server = self._createServer()
        self.__ip_targets.add((server, address, asn))
        return server

    def installByName(self, asn: int, nodename: str) -> Server:
        """!
        @brief Install to node by node name.

        @param asn asn
        @param nodename name of the node

        @returns server instance
        """
        for (s, n, a) in self.__name_targets:
            if a == asn and n == nodename: return s

        server = self._createServer()
        self.__name_targets.add((server, nodename, asn))

        return server

