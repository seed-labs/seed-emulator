from .Service import Service, Server
from .DomainNameService import DomainNameService, DomainNameServer
from seedsim.core import Node, Simulator

class ReverseDomainNameServer(Server):
    """!
    @brief Reverse DNS server.
    """

    def install(self, node: Node):
        pass

class ReverseDomainNameService(Service):
    """!
    @brief Reverse DNS. This service hosts the in-addr.arpa. zone and resolve
    IP addresses to nodename-netname.nodetype.asn.net
    """

    __dns: DomainNameService

    def __init__(self):
        """!
        @brief ReverseDomainNameService constructor

        @param simulator simulator
        """
        super().__init__()
        self.addDependency('DomainNameService', True, False)
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return 'ReverseDomainNameService'

    def _createServer(self) -> Server:
        return ReverseDomainNameServer()

    def _doInstall(self, node: Node, server: Server):
        self._log('setting up "in-addr.arpa." server on as{}/{}...'.format(node.getAsn(), node.getName()))
        dns_s: DomainNameServer = self.__dns.installByName(node.getAsn(), node.getName())
        dns_s.addZone(self.__dns.getZone('in-addr.arpa.'))

    def configure(self, simulator: Simulator):
        reg = simulator.getRegistry()

        self._log('Creating "in-addr.arpa." zone...')
        self.__dns = reg.get('seedsim', 'layer', 'DomainNameService')
        zone = self.__dns.getZone('in-addr.arpa.')

        self._log('Collecting IP addresses...')
        for ([scope, type, name], obj) in reg.getAll().items():
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
                record = '{} PTR {}-{}.{}.{}.net.'.format(addr, name, netname, type, scope).replace('_', '-')
                zone.addRecord(record)

        return super().configure(simulator)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ReverseDomainNameService\n'

        return out
    