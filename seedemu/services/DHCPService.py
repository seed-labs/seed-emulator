from __future__ import annotations
from seedemu import *
from ipaddress import IPv4Address, IPv4Network

DHCPServiceFileTemplates: Dict[str, str] = {}

DHCPServiceFileTemplates['isc_dhcp_server_conf'] = '''
INTERFACESv4="{iface}"
INTERFACESv6=""
'''

DHCPServiceFileTemplates['dhcpd_conf'] = '''
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
  #option domain-name-servers server.example.org;
  #option domain-name "example.org";
  option subnet-mask {netmask};
  option routers {router};
  option broadcast-address {broadcast_address};
  default-lease-time 600;
  max-lease-time 7200;
}}
'''

class DHCPServer(Server):
    """!
    @brief The dynamic host configuration protocol server.
    """
    __node: Node
    __emulator: Emulator

    def configure(self, node: Node, emulator:Emulator):
        """!
        @brief configure the node
        """
        self.__node = node
        self.__emulator = emulator
                

        

    def install(self, node:Node):
        """!
        @brief Install the service
        """

        node.addSoftware('isc-dhcp-server')

        ifaces = self.__node.getInterfaces()
        assert len(ifaces) > 0, 'node {} has no interfaces'.format(node.getName())
        hif: Interface = ifaces[0]
            
        reg = self.__emulator.getRegistry()
        (scope, _, _) = node.getRegistryInfo()
        rif: Interface = None
        
        hnet: Network = hif.getNet()

        cur_scope = ScopedRegistry(scope, reg)
        for router in cur_scope.getByType('rnode'):
            if rif != None: break
            for riface in router.getInterfaces():
                if riface.getNet() == hnet:
                    rif = riface
                    break
        
        subnet = hnet.getPrefix().with_netmask.split('/')[0]
        netmask = hnet.getPrefix().with_netmask.split('/')[1]
        iface_name = hnet.getName()
        router_address = rif.getAddress()
        broadcast_address = hnet.getPrefix().broadcast_address
        ip_start = ip_end = '.'.join(subnet.split(".")[0:3])
        ip_start += ".20"
        ip_end += ".60"

        node.setFile('/etc/default/isc-dhcp-server', DHCPServiceFileTemplates['isc_dhcp_server_conf'].format(iface=iface_name))
        node.setFile('/etc/dhcp/dhcpd.conf', DHCPServiceFileTemplates['dhcpd_conf'].format(
            subnet = subnet,
            netmask = netmask, 
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
