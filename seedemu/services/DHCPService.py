from __future__ import annotations
from seedemu import *
from ipaddress import IPv4Address, IPv4Network

DHCPServiceFileTemplates: Dict[str, str] = {}

DHCPServiceFileTemplates['isc_dhcp_server_conf'] = '''\
INTERFACESv4="{iface}"
INTERFACESv6=""
'''

DHCPServiceFileTemplates['dhcpd_conf'] = '''\
# option definitions common to all supported networks...
# option domain-name "example.org";
# option domain-name-servers server.example.org;

default-lease-time 600;
max-lease-time 7200;

# The ddns-updates-style parameter controls whether or not the server will
# attempt to do a DNS update when a lease is confirmed. We default to the
# behavior of the version 2 packages ('none', since DHCP v2 didn't
# have support for DDNS.)
ddns-update-style none;

# A slightly different configuration for an internal subnet.
subnet {subnet} netmask {netmask} {{
    range {ip_start} {ip_end};
    {name_servers}
    option subnet-mask {netmask};
    option routers {router};
    option broadcast-address {broadcast_address};
    default-lease-time 600;
    max-lease-time 7200;
}}
'''

DHCPServiceFileTemplates['dhcpd_conf_dns'] = '''\
option domain-name-servers {name_servers};\
'''

class DHCPServer(Server):
    """!
    @brief The dynamic host configuration protocol server.
    """
    __node: Node
    __emulator: Emulator
    __name_servers: str
    __dhcp_start: int
    __dhcp_end: int
    __is_range_changed: bool

    def __init__(self):
        """!
        @brief DHCPServer Constructor.
        """
        super().__init__()
        self.__name_servers = "#option domain-name-servers none;"
        self.__is_range_changed = False

    def configure(self, node: Node, emulator:Emulator):
        """!
        @brief configure the node
        """
        self.__node = node
        self.__emulator = emulator

    def setIpRange(self, dhcpStart:int, dhcpEnd: int) -> DHCPServer:
        """!
        @brief set DHCP IP range
        """
        self.__dhcp_start = dhcpStart
        self.__dhcp_end = dhcpEnd
        self.__is_range_changed = True
        
        return self

    def install(self, node:Node):
        """!
        @brief Install the service
        """

        node.addSoftware('isc-dhcp-server')

        ifaces = self.__node.getInterfaces()
        assert len(ifaces) > 0, 'node {} has no interfaces'.format(node.getName())
        
        reg = self.__emulator.getRegistry()
        (scope, _, _) = node.getRegistryInfo()
        rif: Interface = None
        hif: Interface = ifaces[0]
        hnet: Network = hif.getNet()

        cur_scope = ScopedRegistry(scope, reg)
        for router in cur_scope.getByType('rnode'):
            if rif != None: break
            for riface in router.getInterfaces():
                if riface.getNet() == hnet:
                    rif = riface
                    break

        assert rif != None, 'Host {} in as{} in network {}: no router'.format(self.__node.getname, scope, hnet.getName())
                
        subnet = hnet.getPrefix().with_netmask.split('/')[0]
        netmask = hnet.getPrefix().with_netmask.split('/')[1]
        iface_name = hnet.getName()
        router_address = rif.getAddress()
        broadcast_address = hnet.getPrefix().broadcast_address
        
        if (self.__is_range_changed):
            hnet.setDhcpIpRange(self.__dhcp_start, self.__dhcp_end)
            
        ip_address_start, ip_address_end = hnet.getDhcpIpRange()
        ip_start = ip_end = '.'.join(subnet.split(".")[0:3])
        ip_start += "." + ip_address_start
        ip_end += "." + ip_address_end

        nameServers:list = self.__node.getNameServers()

        if len(nameServers) > 0:
            self.__name_servers =  DHCPServiceFileTemplates['dhcpd_conf_dns'].format(name_servers = ", ".join(nameServers))       

        node.setFile('/etc/default/isc-dhcp-server', DHCPServiceFileTemplates['isc_dhcp_server_conf'].format(iface=iface_name))
        node.setFile('/etc/dhcp/dhcpd.conf', DHCPServiceFileTemplates['dhcpd_conf'].format(
            subnet = subnet,
            netmask = netmask, 
            name_servers = self.__name_servers,
            ip_start = ip_start,
            ip_end = ip_end,
            router = router_address, 
            broadcast_address = broadcast_address
        ))

        node.appendStartCommand('/etc/init.d/isc-dhcp-server restart')

    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DHCP server object.\n'

        return out

class DHCPService(Service):
    """!
    @brief The dynamic host configuration protocol service class.
    """

    def __init__(self):
        """!
        @brief DHCPService constructor
        """

        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return DHCPServer()


    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(node, emulator)

    def getName(self) -> str:
        return 'DHCPService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DHCPServiceLayer\n'

        return out
