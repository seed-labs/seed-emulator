from seedsim.core import Node
from .Service import Service, Server
from typing import List

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
        bind9. Use this method to override root hint.

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

class DomainNameCachingService(Service):
    """!
    @brief Caching DNS (i.e., Local DNS)

    @todo DNSSEC
    """

    __auto_root: bool
    __set_resolvconf: bool

    def __init__(self, autoRoot: bool = True, setResolvconf: bool = False):
        """!
        @brief DomainNameCachingService constructor.

        @param autoRoot (optional) find root zone name servers automaically.
        True by defualt, if true, DomainNameCachingService will find root NS in
        DomainNameService and use them as root.
        @param setResolvConf (optional) set all nodes in the AS to use local DNS
        node in the AS by overrideing resolv.conf. Default to false.
        """

        self.__auto_root = autoRoot
        self.__set_resolvconf = setResolvconf

    def getName(self) -> str:
        return 'DomainNameCachingService'

    def getDependencies(self) -> List[str]:
        return ['Base', 'DomainNameService'] if self.__auto_root else ['Base']