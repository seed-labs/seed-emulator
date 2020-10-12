from .Service import Service, Server
from .DomainNameService import DomainNameService, DomainNameServer, Zone
from .Reality import Reality
from seedsim.core import Node, ScopedRegistry, Registry, Network
from typing import List, Tuple
from ipaddress import IPv4Network

class CyrmuIpOriginServer(Server):
    """!
    @brief Cymru's IP info service server.
    """

    __dns_server: DomainNameServer
    __reg = ScopedRegistry('seedsim')
    __dns_server: DomainNameServer
    __node: Node

    def __init__(self, node: Node):
        """!
        @brief CyrmuIpOriginServer constructor.

        @param node node to install on.
        """
        assert self.__reg.has('layer', 'DomainNameService'), 'Please initlize DomainNameService object and add it to renderer fist.'
        dns: DomainNameService = self.__reg.get('layer', 'DomainNameService')
        self.__dns_server = dns.hostZoneOn('cymru.com', node)
        self.__node = node

    def getNode(self) -> Node:
        """!
        @brief get node.

        @returns node.
        """
        return self.__node

    def getDnsServer(self) -> DomainNameServer:
        """!
        @brief get DNS server.

        @returns dns server.
        """
        return self.__dns_server

class CyrmuIpOriginService(Service):
    """!
    @brief Cymru's IP info service.

    Cymru's IP info service is used by various traceroute utilities to map IP
    address to ASN (using DNS). This service loads the prefix list within the
    simulation and creates ASN mappings for them, so with proper local DNS
    configured, nodes can see the ASN when doing traceroute. 

    This layer hosts the domain cymru.com.
    """

    __servers: List[CyrmuIpOriginServer]
    __zone: Zone
    __reg = ScopedRegistry('seedsim')

    def __init__(self):
        """!
        @brief CyrmuIpOriginService constructor
        """
        assert self.__reg.has('layer', 'DomainNameService'), 'Please initlize DomainNameService object first.'
        dns: DomainNameService = self.__reg.get('layer', 'DomainNameService')
        self.__zone = dns.getZone('cymru.com')
        self.__servers = []
        self.addReverseDependency('DomainNameService')

    def getName(self) -> str:
        return 'CyrmuIpOriginService'

    def getDependencies(self) -> List[str]:
        return ['Base']

    def addMapping(self, prefix: str, asn: int):
        """!
        @brief Add new prefix -> asn mapping.

        @param prefix prefix.
        @param asn asn.

        @throws AssertionError if prefix invalid.
        """
        [pfx, cidr] = prefix.split('/')
        cidr = int(cidr)
        assert cidr <= 24, 'Invalid prefix.'
        prefix = IPv4Network(prefix)

        sub_cidr = 24
        num_8s = 3

        if cidr >= 0:
            sub_cidr = 8
            num_8s = 1

        if cidr >= 9:
            sub_cidr = 16
            num_8s = 2

        if cidr >= 17:
            sub_cidr = 24
            num_8s = 3

        for net in prefix.subnets(new_prefix = sub_cidr):
            record = '*.'
            record += '.'.join(reversed(str(net).split('.')[0:3]))
            record += '.origin.asn TXT "{} | {} | ZZ | SEED | 0000-00-00"'.format(asn, net)
            self.__zone.addRecord(record)

    def getZone(self) -> Zone:
        """!
        @brief Get the cyrmu.com zone.

        @returns zone.
        """
        return self.__zone

    def _doInstall(self, node: Node) -> CyrmuIpOriginServer: 
        server = CyrmuIpOriginServer(node)
        self.__servers.append(server)

    def onRender(self):
        mappings: List[Tuple[str, str]] = []

        if self.__reg.has('layer', 'Reality'):
            real: Reality = self.__reg.get('layer', 'Reality')
            for router in real.getRealWorldRouters():
                (asn, _, name) = router.getRegistryInfo()
                asn = int(asn)
                self._log('Collecting real-world route info on as{}/{}...'.format(asn, name))
                for prefix in router.getRealWorldRoutes():
                    mappings.append((prefix, asn))
        
        self._log('Collecting all networks in the simulation...'.format(asn, name))
        for regobj in (Registry()).getAll().items():
            [(asn, type, name), obj] = regobj
            if type != 'net': continue
            net: Network = obj
            if asn == 'ix': asn = name.replace('ix', '')
            mappings.append((net.getPrefix(), int(asn)))

        for mapping in mappings:
            (prefix, asn) = mapping
            self.addMapping(str(prefix), asn)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'CyrmuIpOriginService:\n'
        
        indent += 4
        out += ' ' * indent
        out += 'Installed on:\n'

        indent += 4
        for server in self.__servers:
            (asn, _, name) = server.getNode().getRegistryInfo()
            out += ' ' * indent
            out += 'as{}/{}\n'.format(asn, name)

        return out

