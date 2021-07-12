from __future__ import annotations
from .DomainNameService import DomainNameService
from seedemu.core import Node, Network, Emulator, Service, Server
from typing import List, Tuple
from ipaddress import IPv4Network

class CymruIpOriginServer(Server):
    """!
    @brief Cymru's IP info service server.
    """

    def install(self, node: Node):
        pass

class CymruIpOriginService(Service):
    """!
    @brief Cymru's IP info service.

    Cymru's IP info service is used by various traceroute utilities to map IP
    address to ASN (using DNS). This service loads the prefix list within the
    simulation and creates ASN mappings for them, so with proper local DNS
    configured, nodes can see the ASN when doing traceroute. 

    This layer hosts the domain cymru.com.
    """

    __records: List[str]
    __dns: DomainNameService

    def __init__(self):
        """!
        @brief CymruIpOriginService constructor
        """
        super().__init__()
        self.__records = []
        self.addDependency('DomainNameService', True, True)
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return CymruIpOriginServer()

    def getName(self) -> str:
        return 'CymruIpOriginService'

    def addMapping(self, prefix: str, asn: int) -> CymruIpOriginService:
        """!
        @brief Add new prefix -> asn mapping.

        @param prefix prefix.
        @param asn asn.

        @throws AssertionError if prefix invalid.

        @returns self, for chaining API calls.
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

        return self

    def getRecords(self) -> List[str]:
        """!
        @brief get generated records.

        @return list of records.
        """
        return self.__records

    def addRecord(self, record: str) -> CymruIpOriginService:
        """!
        @brief add record directly to the cymru zone. You should use addMapping
        to add mapping and not addRecord, unless you know what you are doing.

        @returns self, for chaining API calls.
        """
        self.__records.append(record)

        return self

    def _doInstall(self, node: Node, server: Server): 
        assert False, 'CymruIpOriginService is not a real service and should not be installed this way. Please install a DomainNameService on the node and host the zone "cymru.com." yourself.'


    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()

        mappings: List[Tuple[str, str]] = []
        
        self._log('Collecting all networks in the simulation...')
        for regobj in reg.getAll().items():
            [(asn, type, name), obj] = regobj
            if type != 'net': continue
            net: Network = obj
            if asn == 'ix': asn = name.replace('ix', '')
            
            asn_val = 0
            try:
                asn_val = int(asn)
            except ValueError:
                asn_val = 0

            mappings.append((net.getPrefix(), asn_val))

        for mapping in mappings:
            (prefix, asn) = mapping
            self.addMapping(str(prefix), asn)

        self._log('Creating "cymru.com." zone...')
        dns: DomainNameService = reg.get('seedemu', 'layer', 'DomainNameService')
        zone = dns.getZone('cymru.com.')
        self.__dns = dns

        self._log('Adding mappings...')
        for record in self.__records:
            zone.addRecord(record)

        return super().configure(emulator)        

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'CymruIpOriginService\n'

        return out

