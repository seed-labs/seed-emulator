from .Ospf import Ospf
from .Ibgp import Ibgp
from .Routing import Router
from seedsim.core import Layer
from typing import Dict, Tuple, List, Set

EvpnFileTemplates: Dict[str, str] = {}

EvpnFileTemplates['frr_start_script'] = '''\
#!/bin/bash
sed -i 's/ldpd=no/ldpd=yes/' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
service frr start
'''

EvpnFileTemplates['vetp_bridge'] = '''\
auto br-{name}
iface br-{name} inet manual
    pre-up          ip link add br-{name} type bridge stp_state 0
    post-down       ip link del br-{name}

auto vtep-{name}
iface vtep-{name} inet manual
    pre-up          ip link add vtep-{name} type vxlan id {vni} dstport 4789 local {loopbackAddress}
    pre-up          ip link set vtep-{name} master br-{name}
    post-down       ip link del vtep-{name}
'''

EvpnFileTemplates['rr_config'] = '''\
ip router-id {routerId}
!
{ospfInterfaces}
!
router bgp {asn}
    no bgp default ipv4-unicast
    neighbor fabric peer-group
    neighbor fabric remote-as {asn}
    neighbor fabric update-source {loopbackAddress}
    neighbor fabric capability dynamic
    neighbor fabric capability extended-nexthop
    neighbor fabric graceful-restart
{neighbours}
    !
    address-family l2vpn evpn
        neighbor fabric activate
        neighbor fabric route-reflector-client
        neighbor fabric soft-reconfiguration inbound
    exit-address-family
!
'''

EvpnFileTemplates['rr_config_neighbor'] = '''\
    neighbor {neighbourAddress} peer-group fabric
'''

EvpnFileTemplates['ospf_interface'] = '''\
interface {interface}
    ip ospf area 0
    ip ospf dead-interval minimal hello-multiplier 2
'''

EvpnFileTemplates['pe_config'] = '''\
ip router-id {routerId}
!
{ospfInterfaces}
!
router bgp {asn}
    no bgp default ipv4-unicast
    neighbor {rrAddress} remote-as {asn}
    neighbor {rrAddress} update-source {loopbackAddress}
    neighbor {rrAddress} capability dynamic
    neighbor {rrAddress} capability extended-nexthop
    neighbor {rrAddress} graceful-restart
    !
    address-family l2vpn evpn
        neighbor {rrAddress} activate
        neighbor {rrAddress} soft-reconfiguration inbound
        advertise-all-vni
        advertise-svi-ip
    exit-address-family
!
'''

class Evpn(Layer):
    """!
    @brief The Evpn (Ethernet VPN) layer.

    This layer add supports for BGP-signeled EVPN.
    """

    __customers: Set[Tuple[int, int, str, str, int]]
    __providers: Set[int]

    def __init__(self):
        super().__init__()

        # they are not really "dependency," we just need them to render after
        # us, in case we need to setup masks.
        self.addDependency('Ospf', True, True)
        self.addDependency('Ibgp', True, True)

        self.addDependency('Routing', False, False)

        self.__customers = set()
        self.__providers = set()

    def getName(self) -> str:
        return 'Evpn'
        
    def configureAsEvpnProvider(self, asn: int):
        '''!
        @brief configure an AS to be EVPN provider; currently, making an EVPN
        provider will exclude it from any IP-based network.

        @param asn asn.
        '''
        self.__providers.add(asn)

    def getEvpnProviders(self) -> Set[int]:
        '''!
        @brief get set of EVPN providers.
        
        @returns set of asns.
        '''
        return self.__providers

    def addCustomer(self, providerAsn: int, customerAsn: int, customerNetworkName: str, providerRouterNodeName: str, vni: int):
        '''!
        @brief add a customer.

        @param providerAsn provider ASN.
        @param customerAsn customer ASN. If the target network is an internet
        exchange, use 0 as asn.
        @param customerNetworkName customer network name.
        @param routerNodeName name of the PE router node.
        @param vni VNI.
        '''
        self.__customers.add((providerAsn, customerAsn, customerNetworkName, providerRouterNodeName, vni))

    def getCustomers(self) -> Set[Tuple[int, int, str, str, int]]:
        '''!
        @brief Get set of customers.

        @return set of (provider asn, customer asn, customer netname, pe node name)
        '''
        return self.__customers
    