from .Service import Service, Server
from .DomainNameService import DomainNameService, DomainNameServer, Zone
from seedsim.core import ScopedRegistry, Registry, Node
from typing import List

class ReverseDomainNameServer(Server):
    """!
    @brief Reverse DNS server.
    """

    __node: Node

    def __init__(self, node: Node):
        """!
        @brief ReverseDnsServer constructor.

        @param node node to install on.
        """
        self.__node = node

    def getNode(self) -> Node:
        """!
        @brief get node.

        @returns node.
        """
        return self.__node

class ReverseDomainNameService(Service):
    """!
    @brief Reverse DNS. This service hosts the in-addr.arpa. zone and resolve
    IP addresses to nodename-netname.nodetype.asn.net
    """

    __servers: List[ReverseDomainNameServer]
    __reg = ScopedRegistry('seedsim')

    def __init__(self):
        """!
        @brief ReverseDomainNameService constructor
        """
        self.__records = []
        self.__servers = []
        self.addReverseDependency('DomainNameService')

    def getName(self) -> str:
        return 'ReverseDomainNameService'

    def getDependencies(self) -> List[str]:
        return ['Base']

    def _doInstall(self, node: Node) -> ReverseDomainNameServer:
        server = ReverseDomainNameServer(node)
        self.__servers.append(server)

    def onRender(self):
        self._log('Creating "in-addr.arpa." zone...')
        dns: DomainNameService = self.__reg.get('layer', 'DomainNameService')
        zone = dns.getZone('in-addr.arpa.')

        self._log('Collecting IP addresses...')
        for ([scope, type, name], obj) in Registry().getAll().items():
            if type != 'rnode' and type != 'hnode': continue
            self._log('Collecting {}/{}/{}...'.format(scope, type, name))

            if scope == 'ix':
                scope = name
                name = 'rs'
            else: scope = 'as' + scope

            node: Node = obj
            for iface in node.getInterfaces():
                addr = '.'.join(reversed(str(iface.getAddress()).split('.')))
                netname = iface.getNet().getName()
                record = '{} PTR {}-{}.{}.{}.net.'.format(addr, name, netname, type, scope)
                zone.addRecord(record)

        self._log('Setting up "in-addr.arpa." server nodes...')
        for server in self.__servers:
            dns.hostZoneOn('in-addr.arpa.', server.getNode())

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ReverseDomainNameService:\n'
        
        indent += 4
        out += ' ' * indent
        out += 'Installed on:\n'

        indent += 4
        for server in self.__servers:
            (asn, _, name) = server.getNode().getRegistryInfo()
            out += ' ' * indent
            out += 'as{}/{}\n'.format(asn, name)

        return out


        
    