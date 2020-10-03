from __future__ import annotations
from .Service import Service, Server
from seedsim.core import Node, Printable
from seedsim.core.enums import NodeRole
from typing import List, Dict, Tuple, Set
from re import sub

class Zone(Printable):
    """!
    @brief Domain name zone.
    """
    __zonename: str
    __subzones: Dict[str, Zone]
    __records: List[str]
    __gules: List[str]

    def __init__(self, name: str):
        """!
        @brief Zone constructor.
        
        @param name full zonename.
        """
        self.__zonename = name
        self.__subzones = {}
        self.__records = []
        self.__gules = []

    def getName(self) -> str:
        """!
        @brief Get zonename.

        @returns zonename.
        """
        return self.__zonename

    def getSubZone(self, name: str) -> Zone:
        """!
        @brief Get a subzone, if not exists, a new one will be created.

        @param name partial zonename. For example, if current zone is "com.", to
        get "example.com.", use getSubZone("example")

        @returns zone.
        @throws AssertionError if invalid zonename.
        """
        assert '.' not in name, 'invalid subzone name "{}"'.format(name)
        if name in self.__subzones: return self.__subzones[name]
        self.__subzones[name] = Zone('{}.{}'.format(name, self.__zonename))
        return self.__subzones[name]
    
    def getSubZones(self) -> Dict[str, Zone]:
        """!
        @brief Get all subzones.

        @return subzones dict.
        """
        return self.__subzones

    def addRecord(self, record: str):
        """!
        @brief Add a new record to zone.

        @todo NS?
        """
        self.__records.append(record)

    def addGuleRecord(self, fqdn: str, addr: str):
        """!
        @brief Add a new gule record.

        Use this method to register a name server in the parent zone.

        @param fqdn full domain name of the name server.
        @param addr IP address of the name server.
        """
        if fqdn[-1] != '.': fqdn += '.'
        self.__gules.append('{} A {}'.format(fqdn, addr))
        self.__gules.append('{} NS {}'.format(self.__zonename, fqdn))


    def getRecords(self) -> List[str]:
        """!
        @brief Get all records.

        @return list of records.
        """
        return self.__records

    def getGuleRecords(self) -> List[str]:
        """!
        @brief Get all gule records.

        @return list of records.
        """
        return self.__gules

    def findRecords(self, keyword: str) -> List[str]:
        """!
        @brief Find a record.

        @param keyword keyword.

        @return list of records.
        """
        return [ r for r in self.__records if keyword in r ]

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Zone "{}":\n'.format(self.__zonename)

        indent += 4
        out += ' ' * indent
        out += 'Records:\n'

        indent += 4
        for record in self.__records:
            out += ' ' * indent
            out += '{}\n'.format(record)

        indent -= 4
        out += ' ' * indent
        out += 'Subzones:\n'
        
        indent += 4
        for subzone in self.__subzones.values():
            out += subzone.print(indent)

        return out

class DomainNameServer(Server):
    """!
    @brief The domain name server.
    """

    __node: Node
    __zones: Set[Zone]

    def __init__(self, node: Node):
        self.__node = node
        self.__zones = set()

    def addZone(self, zone: Zone):
        self.__zones.add(zone)

    def getZones(self) -> List[Zone]:
        return list(self.__zones)

class DomainNameService(Service):
    """!
    @brief The domain name service.
    """

    __rootZone: Zone = Zone('') # singleton
    __servers: List[DomainNameServer]

    def __init__(self):
        self.__servers = []

    def getName(self):
        return 'DomainNameService'

    def getZone(self, domain: str) -> Zone:
        """!
        @brief Get a zone, create it if not exist.

        This method only create the zone. Host it with hostZoneOn.

        @param domain zone name.

        @returns zone handler.
        """
        path: List[str] = sub(r'\.$', '', domain).split('.')
        path.reverse()
        zoneptr = self.__rootZone
        for z in path:
            zoneptr = zoneptr.getSubZone(z)

        return zoneptr

    def getRootZone(self) -> Zone:
        """!
        @brief Get the root zone.

        @return root zone.
        """
        return self.__rootZone

    def _doInstall(self, node: Node) -> DomainNameServer:
        server: DomainNameServer = node.getAttribute('__domain_name_service_server')
        if server != None: return server
        server = DomainNameServer(node)
        self.__servers.append(server)
        node.setAttribute('__domain_name_service_server', server)
        return server

    def hostZoneOn(self, domain: str, node: Node, addNsAndSoa: bool = True):
        """!
        @brief Host a zone on the given node.

        Zone must be created with getZone first.

        @param domain zone name.
        @param node target node.
        @param addNsAndSoa (optional) add NS (ns1.domain.tld) and SOA records
        automatically, true by default. This method will also add gule records.

        @throws AssertionError if node is not a host node.
        @throws AssertionError if node has no interface.
        """
        if not node.hasAttribute('__domain_name_service_server'):
            self.installOn(node)

        server: DomainNameServer = node.getAttribute('__domain_name_service_server')
        zone = self.getZone(domain)
        server.addZone(zone)

        if not addNsAndSoa: return

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'node has not interfaces'
        addr = ifaces[0].getAddress()

        if len(zone.findRecords('SOA')) == 0:
            zone.addRecord('@ SOA TODO TODO TODO')

        if domain[-1] != '.': domain += '.'
        zone.addGuleRecord('ns1.{}'.format(domain), addr)
        zone.addRecord('ns1.{} A {}'.format(domain, addr))
        zone.addRecord('@ NS ns1.{}'.format(domain))

    def __autoNameServer(self, zone: Zone):
        if (len(zone.getSubZones().values()) == 0): return
        for subzone in zone.getSubZones().values():
            for gule in subzone.getGuleRecords(): zone.addRecord(gule)
            self.__autoNameServer(subzone)

    def autoNameServer(self):
        """!
        @brief Try to automatically add NS records of children to parent zones.

        Note that all zones in the simulation must have NS record for this to
        work.
        """
        self.__autoNameServer(self.__rootZone)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameService:\n'

        indent += 4
        out += self.__rootZone.print(indent)

        return out