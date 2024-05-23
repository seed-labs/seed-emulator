from __future__ import annotations
from seedemu.core import Configurable, Service, Server
from seedemu.core import Node, ScopedRegistry, Emulator
from .DomainNameService import DomainNameService
from typing import List, Dict
from seedemu.core.enums import NetworkType

DomainNameCachingServiceFileTemplates: Dict[str, str] = {}

DomainNameCachingServiceFileTemplates['named_options'] = '''\
options {
    directory "/var/cache/bind";
    recursion yes;
    dnssec-validation no;
    empty-zones-enable no;
    allow-query { any; };
};
'''

class DomainNameCachingServer(Server, Configurable):
    """!
    @brief Caching DNS server (i.e., Local DNS server)

    @todo DNSSEC
    """

    __root_servers: List[str]
    __configure_resolvconf: bool
    __emulator: Emulator
    __pending_forward_zones: Dict[str, str]
    __asn_range: List[int]
    __is_range_all: bool

    def __init__(self):
        """!
        @brief DomainNameCachingServer constructor.
        """
        super().__init__()
        self.__root_servers = []
        self.__configure_resolvconf = False
        self.__pending_forward_zones = {}
        self.__asn_range = []
        self.__is_range_all = False

    def setConfigureResolvconf(self, configure: bool) -> DomainNameCachingServer:
        """!
        @brief Enable or disable set resolv.conf. When true, resolv.conf of all
        other nodes in the AS will be set to this server.

        @returns self, for chaining API calls.
        """
        self.__configure_resolvconf = configure

        return self

    def setRootServers(self, servers: List[str]) -> DomainNameCachingServer:
        """!
        @brief Change root server hint.

        By default, the caching server uses the root hint file shipped with
        bind9. Use this method to override root hint. Note that if autoRoot is
        set to true in DomainNameCachingService, manual changes will be
        overridden.

        @param servers list of IP addresses of the root servers.

        @returns self, for chaining API calls.
        """
        self.__root_servers = servers

        return self

    def getRootServers(self) -> List[str]:
        """!
        @brief Get root server list.

        By default, the caching server uses the root hint file shipped with
        bind9. Use setRootServers to override root hint.

        This method will return list of servers set by setRootServers, or an
        empty list if not set.
        """
        return self.__root_servers

    def addForwardZone(self, zone: str, vnode: str) -> DomainNameCachingServer:
        """!
        @brief Add a new forward zone, forward to the given virtual node name.

        @param name zone name.
        @param vnode  virtual node name.

        @returns self, for chaining API calls.
        """
        self.__pending_forward_zones[zone] = vnode

        return self
    
    def setNameServerOnNodesByAsns(self, asns: List[int]):
        self.__asn_range.extend(asns)

    def setNameServerOnAllNodes(self):
        self.__is_range_all = True

    def configure(self, emulator: Emulator, node:Node):
        self.__emulator = emulator

        reg = emulator.getRegistry()
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        
        assert address != "", 'address is not configured.'

        for ((scope, type, name), node) in reg.getAll().items():
            if type in ['hnode', 'rnode']:
                if self.__is_range_all or node.getAsn() in self.__asn_range:
                    if not any(command[0] == ': > /etc/resolv.conf' for command in node.getStartCommands()):
                        node.insertStartCommand(0,': > /etc/resolv.conf')
                    node.insertStartCommand(1, 'echo "nameserver {}" >> /etc/resolv.conf'.format(address))
    
    def install(self, node: Node):
        node.addSoftware('bind9')
        node.setFile('/etc/bind/named.conf.options', DomainNameCachingServiceFileTemplates['named_options'])
        node.setFile('/etc/bind/named.conf.local','')
        if len(self.__root_servers) > 0:
            hint = '\n'.join(self.__root_servers)
            node.setFile('/usr/share/dns/root.hints', hint)
            node.setFile('/etc/bind/db.root', hint)
        node.appendStartCommand('service named start')

        for (zone_name, vnode_name) in self.__pending_forward_zones.items():
            pnode = self.__emulator.resolvVnode(vnode_name)

            ifaces = pnode.getInterfaces()
            assert len(ifaces) > 0, 'resolvePendingRecords(): node as{}/{} has no interfaces'.format(pnode.getAsn(), pnode.getName())
            vnode_addr = ifaces[0].getAddress()
            node.appendFile('/etc/bind/named.conf.local',
                        'zone "{}" {{ type forward; forwarders {{ {}; }}; }};\n'.format(zone_name, vnode_addr))

        if not self.__configure_resolvconf: return

        reg = self.__emulator.getRegistry()
        (scope, _, _) = node.getRegistryInfo()
        sr = ScopedRegistry(scope, reg)
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        addr = ifaces[0].getAddress()

        for rnode in sr.getByType('rnode'):
            rnode.appendFile('/etc/resolv.conf.new', 'nameserver {}\n'.format(addr))
            if 'cat /etc/resolv.conf.new > /etc/resolv.conf' not in rnode.getStartCommands():
                rnode.appendStartCommand('cat /etc/resolv.conf.new > /etc/resolv.conf')

        for hnode in sr.getByType('hnode'):
            if 'cat /etc/resolv.conf.new > /etc/resolv.conf' not in hnode.getStartCommands():
                hnode.appendStartCommand('cat /etc/resolv.conf.new > /etc/resolv.conf')
            hnode.appendFile('/etc/resolv.conf.new', 'nameserver {}\n'.format(addr))

class DomainNameCachingService(Service):
    """!
    @brief Caching DNS (i.e., Local DNS)

    @todo DNSSEC
    """

    __auto_root: bool

    def __init__(self, autoRoot: bool = True):
        """!
        @brief DomainNameCachingService constructor.

        @param autoRoot (optional) find root zone name servers automatically.
        True by default, if true, DomainNameCachingService will find root NS in
        DomainNameService and use them as root.
        """
        super().__init__()
        self.__auto_root = autoRoot
        self.addDependency('Base', False, False)
        if autoRoot:
            self.addDependency('DomainNameService', False, False)

    def _createServer(self) -> DomainNameCachingServer:
        return DomainNameCachingServer()

    def getName(self) -> str:
        return 'DomainNameCachingService'

    def getConflicts(self) -> List[str]:
        return ['DomainNameService']

    def __getIpAddr(self, node:Node) -> str:
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                return address
            
        return ""
    
    def configure(self, emulator: Emulator):
        super().configure(emulator)

        targets = self.getTargets()
        ipaddrs = []
        for (server, node) in targets:
            server.configure(emulator, node)

            address = self.__getIpAddr(node)
            assert address != "", 'address is not configured.'
            ipaddrs.append(address)

        # For the nodes that are not covered, all the local DNS servers will be added to them (the default behavior).
        reg = emulator.getRegistry()
        for ((scope, type, name), node) in reg.getAll().items():
            if type in ['hnode', 'rnode']:
                if not any(command[0] == ': > /etc/resolv.conf' for command in node.getStartCommands()):
                    node.insertStartCommand(0,': > /etc/resolv.conf')
                    for s in (ipaddrs):
                        node.insertStartCommand(1, 'echo "nameserver {}" >> /etc/resolv.conf'.format(s))

        if self.__auto_root:
            dns_layer: DomainNameService = emulator.getRegistry().get('seedemu', 'layer', 'DomainNameService')
            root_zone = dns_layer.getRootZone()
            root_servers = root_zone.getGuleRecords()
            for (server, node) in targets:
                server.setRootServers(root_servers)

 
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameCachingService:\n'

        indent += 4

        out += ' ' * indent
        out += 'Configure root hint: {}\n'.format(self.__auto_root)

        return out