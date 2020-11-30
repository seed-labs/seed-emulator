from __future__ import annotations
from .Service import Service, Server
from seedsim.core import Node, Printable, ScopedRegistry
from seedsim.core.enums import NodeRole, NetworkType
from typing import List, Dict, Tuple, Set
from re import sub
from random import randint

DomainNameServiceFileTemplates: Dict[str, str] = {}

DomainNameServiceFileTemplates['named_options'] = '''\
options {
	directory "/var/cache/bind";
	recursion no;
	dnssec-validation no;
    empty-zones-enable no;
	allow-query { any; };
    allow-update { any; };
};
'''

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
        self.__records = [
            '$TTL 300',
            '$ORIGIN {}'.format(name if name != '' else '.')
        ]
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
        zonename = self.__zonename if self.__zonename != '' else '.' 
        self.__gules.append('{} A {}'.format(fqdn, addr))
        self.__gules.append('{} NS {}'.format(zonename, fqdn))

    def resolveTo(self, name: str, node: Node):
        """!
        @brief Add a new A record, pointing to the given node.

        @param name name.
        @param node node.

        @throws AssertionError if node does not have valid interfaces.
        """

        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node has no interfaces.'
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Host or net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break

        assert address != None, 'Node has no valid interfaces.'
        self.__records.append('{} A {}'.format(name, address))

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
        zonename = self.__zonename if self.__zonename != '' else '(root zone)'
        out += 'Zone "{}":\n'.format(zonename)

        indent += 4
        out += ' ' * indent
        out += 'Zonefile:\n'

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
        """!
        @brief DomainNameServer constructor.

        @param node node to install server on.
        """
        self.__node = node
        self.__zones = set()

    def addZone(self, zone: Zone):
        """!
        @brief Add a zone to this node.

        You should use DomainNameService.hostZoneOn to host zone on node if you
        want the automated NS record to work.
        """
        self.__zones.add(zone)

    def getZones(self) -> List[Zone]:
        """!
        @brief Get list of zones hosted on the node.

        @returns list of zones.
        """
        return list(self.__zones)

    def getNode(self) -> Node:
        """!
        @brief Get the node.

        @returns node.
        """
        return self.__node

    def print(self, indent: int) -> str:
        out = ' ' * indent
        (scope, _, name) = self.__node.getRegistryInfo()
        out += 'Zones on as{}/{}:\n'.format(scope, name)
        indent += 4
        for zone in self.__zones:
            out += ' ' * indent
            zname = zone.getName()
            if zname == '' or zname[-1] != '.': zname += '.'
            out += '{}\n'.format(zname)

        return out

    def install(self):
        """!
        @brief Handle the installation.
        """
        self.__node.addSoftware('bind9')
        self.__node.addStartCommand('echo "include \\"/etc/bind/named.conf.zones\\";" >> /etc/bind/named.conf.local')
        self.__node.setFile('/etc/bind/named.conf.options', DomainNameServiceFileTemplates['named_options'])

        for zone in self.__zones:
            zonename = filename = zone.getName()
            if zonename == '' or zonename == '.':
                filename = 'root'
                zonename = '.'
            zonepath = '/etc/bind/zones/{}'.format(filename)
            self.__node.setFile(zonepath, '\n'.join(zone.getRecords()))
            self.__node.appendFile('/etc/bind/named.conf.zones',
                'zone "{}" {{ type master; file "{}"; allow-update {{ any; }}; }};\n'.format(zonename, zonepath)
            )

        self.__node.addStartCommand('chown -R bind:bind /etc/bind/zones')
        self.__node.addStartCommand('service named start')
    
class DomainNameService(Service):
    """!
    @brief The domain name service.
    """

    __rootZone = Zone('') # singleton
    __servers: List[DomainNameServer]
    __reg = ScopedRegistry('seedsim')
    __autoNs: bool

    def __init__(self, autoNameServer: bool = True):
        """!
        @brief DomainNameService constructor.
        
        @param autoNameServer add gule records to parents automaically.
        """
        self.__autoNs = autoNameServer
        self.__servers = []

    def getName(self):
        return 'DomainNameService'

    def getConflicts(self) -> List[str]:
        return ['DomainNameCachingService']
    
    def getDependencies(self) -> List[str]:
        return ['Base']

    def getZone(self, domain: str) -> Zone:
        """!
        @brief Get a zone, create it if not exist.

        This method only create the zone. Host it with hostZoneOn.

        @param domain zone name.

        @returns zone handler.
        """
        if domain == '.' or domain == '': return self.__rootZone
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

        if domain[-1] != '.': domain += '.'
        if domain == '.': domain = ''

        if len(zone.findRecords('SOA')) == 0:
            zone.addRecord('@ SOA {} {} {} 900 900 1800 60'.format('ns1.{}'.format(domain), 'admin.{}'.format(domain), randint(1, 0xffffffff)))

        zone.addGuleRecord('ns1.{}'.format(domain), addr)
        zone.addRecord('ns1.{} A {}'.format(domain, addr))
        zone.addRecord('@ NS ns1.{}'.format(domain))

    def getServerByZoneName(self, zonename: str) -> DomainNameServer:
        """!
        @brief Get server by zonename.

        @param zonename zonename.

        @returns server if exists, None otherwise.
        """

        if zonename[-1] != '.': zonename += '.'
        if zonename == '.': zonename = ''
        for server in self.__servers:
            for zone in server.getZones():
                if zone.getName() == zonename: return server

        return None

    def __autoNameServer(self, zone: Zone):
        """!
        @brief Try to automatically add NS records of children to parent zones.

        @param zone root zone reference.
        """
        if (len(zone.getSubZones().values()) == 0): return
        self._log('Collecting subzones NSes of "{}"...'.format(zone.getName()))
        for subzone in zone.getSubZones().values():
            for gule in subzone.getGuleRecords(): zone.addRecord(gule)
            self.__autoNameServer(subzone)

    def onRender(self):
        if self.__autoNs:
            self._log('Setting up NS records...')
            self.__autoNameServer(self.__rootZone)

        for server in self.__servers:
            server.install()

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameService:\n'

        indent += 4
        out += self.__rootZone.print(indent)

        out += ' ' * indent
        out += 'Hosted zones:\n'

        for server in self.__servers:
            out += server.print(indent + 4)

        return out