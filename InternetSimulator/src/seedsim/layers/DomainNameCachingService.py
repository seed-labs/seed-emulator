from seedsim.core import Node, ScopedRegistry
from .Service import Service, Server
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

class DomainNameCachingServer(Server):
    """!
    @brief Caching DNS server (i.e., Local DNS server)

    @todo DNSSEC
    """

    __root_servers: List[str]
    __node: Node

    def __init__(self, node: Node):
        """!
        @brief DomainNameCachingServer constructor.

        @param node node to install on.
        """
        self.__root_servers = []
        self.__node = node

    def setRootServers(self, servers: List[str]):
        """!
        @brief Change root server hint.

        By defualt, the caching server uses the root hint file shipped with
        bind9. Use this method to override root hint. Note that if autoRoot is
        set to true in DomainNameCachingService, manual changes will be
        overrided.

        @param servers list of IP addresses of the root servers.
        """
        self.__root_servers = servers

    def getRootServers(self) -> List[str]:
        """!
        @brief Get root server list.

        By defualt, the caching server uses the root hint file shipped with
        bind9. Use setRootServers to override root hint.

        This method will return list of servers set by setRootServers, or an
        empty list if not set.
        """
        return self.__root_servers

    def install(self, setResolvconf: bool):
        """!
        @brief Handle installation.

        @param setResolvconf set resolv.conf of all other nodes in the AS.

        @throw AssertionError if setResolvconf is true but current node has no
        IP address.
        """
        self.__node.addSoftware('bind9')
        self.__node.setFile('/etc/bind/named.conf.options', DomainNameCachingServiceFileTemplates['named_options'])
        if len(self.__root_servers) > 0:
            hint = '\n'.join(self.__root_servers)
            self.__node.setFile('/usr/share/dns/root.hints', hint)
            self.__node.setFile('/etc/bind/db.root', hint)
        self.__node.addStartCommand('service named start')
        if not setResolvconf: return
        (scope, _, _) = self.__node.getRegistryInfo()
        sr = ScopedRegistry(scope)
        ifaces = self.__node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(self.__node.getName())
        addr = ifaces[0].getAddress()

        for rnode in sr.getByType('rnode'):
            rnode.appendFile('/etc/resolv.conf.new', 'nameserver {}\n'.format(addr))
            if 'cp /etc/resolv.conf.new /etc/resolv.conf' not in rnode.getStartCommands():
                rnode.addStartCommand('cp /etc/resolv.conf.new /etc/resolv.conf')

        for hnode in sr.getByType('hnode'):
            if 'cp /etc/resolv.conf.new /etc/resolv.conf' not in hnode.getStartCommands():
                hnode.addStartCommand('cp /etc/resolv.conf.new /etc/resolv.conf')
            hnode.appendFile('/etc/resolv.conf.new', 'nameserver {}\n'.format(addr))

class DomainNameCachingService(Service):
    """!
    @brief Caching DNS (i.e., Local DNS)

    @todo DNSSEC
    """

    __auto_root: bool
    __set_resolvconf: bool
    __reg = ScopedRegistry('seedsim')
    __servers: List[DomainNameCachingServer]

    def __init__(self, autoRoot: bool = True, setResolvconf: bool = False):
        """!
        @brief DomainNameCachingService constructor.

        @param autoRoot (optional) find root zone name servers automaically.
        True by defualt, if true, DomainNameCachingService will find root NS in
        DomainNameService and use them as root.
        @param setResolvconf (optional) set all nodes in the AS to use local DNS
        node in the AS by overrideing resolv.conf. Default to false.
        """

        self.__auto_root = autoRoot
        self.__set_resolvconf = setResolvconf
        self.__servers = []

    def getName(self) -> str:
        return 'DomainNameCachingService'

    def getConflicts(self) -> List[str]:
        return ['DomainNameService']

    def getDependencies(self) -> List[str]:
        return ['Base', 'DomainNameService'] if self.__auto_root else ['Base']

    def _doInstall(self, node: Node) -> DomainNameCachingServer:
        """!
        @brief Install the cache service on given node.

        @param node node to install the cache service on.

        @returns Handler of the installed cache service.
        @throws AssertionError if node is not host node.
        """
        server: DomainNameCachingServer = node.getAttribute('__domain_name_cacheing_service_server')
        if server != None: return server
        server = DomainNameCachingServer(node)
        self.__servers.append(server)
        node.setAttribute('__domain_name_cacheing_service_server', server)
        return server

    def onRender(self):
        root_servers: List[str] = []
        if self.__auto_root:
            dns_layer: DomainNameService = self.__reg.get('layer', 'DomainNameService')
            root_zone = dns_layer.getRootZone()
            root_servers = root_zone.getGuleRecords()
        
        for server in self.__servers:
            server.setRootServers(root_servers)
            server.install(self.__set_resolvconf)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameCachingService:\n'

        indent += 4

        out += ' ' * indent
        out += 'Configure root hint: {}\n'.format(self.__auto_root)

        out += ' ' * indent
        out += 'Set resolv.conf: {}\n'.format(self.__set_resolvconf)

        return out