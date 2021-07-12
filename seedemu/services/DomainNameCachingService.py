from __future__ import annotations
from seedemu.core import Configurable, Service, Server
from seedemu.core import Node, ScopedRegistry, Emulator
from .DomainNameService import DomainNameService
from typing import List, Dict

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

    def __init__(self):
        """!
        @brief DomainNameCachingServer constructor.
        """
        self.__root_servers = []
        self.__configure_resolvconf = False

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

        By defualt, the caching server uses the root hint file shipped with
        bind9. Use this method to override root hint. Note that if autoRoot is
        set to true in DomainNameCachingService, manual changes will be
        overrided.

        @param servers list of IP addresses of the root servers.

        @returns self, for chaining API calls.
        """
        self.__root_servers = servers

        return self

    def getRootServers(self) -> List[str]:
        """!
        @brief Get root server list.

        By defualt, the caching server uses the root hint file shipped with
        bind9. Use setRootServers to override root hint.

        This method will return list of servers set by setRootServers, or an
        empty list if not set.
        """
        return self.__root_servers

    def configure(self, emulator: Emulator):
        self.__emulator = emulator

    def install(self, node: Node):
        node.addSoftware('bind9')
        node.setFile('/etc/bind/named.conf.options', DomainNameCachingServiceFileTemplates['named_options'])
        if len(self.__root_servers) > 0:
            hint = '\n'.join(self.__root_servers)
            node.setFile('/usr/share/dns/root.hints', hint)
            node.setFile('/etc/bind/db.root', hint)
        node.appendStartCommand('service named start')

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

        @param autoRoot (optional) find root zone name servers automaically.
        True by defualt, if true, DomainNameCachingService will find root NS in
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

    def configure(self, emulator: Emulator):
        super().configure(emulator)

        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(emulator)

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