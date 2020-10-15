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

    __node: Node

    def __init__(self, node: Node):
        """!
        @brief CyrmuIpOriginServer constructor.

        @param node node to install on.
        """
        self.__node = node

    def getNode(self) -> Node:
        """!
        @brief get node.

        @returns node.
        """
        return self.__node

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
    __records: List[str]
    __reg = ScopedRegistry('seedsim')

    def __init__(self):
        """!
        @brief CyrmuIpOriginService constructor
        """
        self.__records = []
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
            self.__records.append(record)

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

        self._log('Creating "cymru.com." zone...')
        dns: DomainNameService = self.__reg.get('layer', 'DomainNameService')
        zone = dns.getZone('cymru.com.')

        self._log('Setting up "cymru.com." server nodes...')
        for server in self.__servers:
            dns.hostZoneOn('cymru.com.', server.getNode())

        self._log('Adding mappings...')
        for record in self.__records:
            zone.addRecord(record)

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

