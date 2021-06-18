from .Ospf import Ospf
from .Ibgp import Ibgp
from .Routing import Router
from seedemu.core import Layer, Emulator, ScopedRegistry, Registry
from seedemu.core.enums import NetworkType, NodeRole
from typing import Dict, Tuple, List, Set

EvpnFileTemplates: Dict[str, str] = {}

EvpnFileTemplates['frr_start_script'] = '''\
#!/bin/bash
sed -i 's/ldpd=no/ldpd=yes/' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
[ -e /vnis.txt ] && {
    while read -r vnis; do {
        echo "configuring bridge and vtep for vni $vni..."
        ifup br-$vni
        ifup vtep-$vni
    }; done < /vnis.txt
}
[ -e /evpn_customers.txt ] && {
    while read -r line; do {
        echo "connecting customer $vni..."

        vni="`cut -d, -f1 <<< "$line"`"
        netname="`cut -d, -f1 <<< "$line"`"

        ip addr flush $netname
        ip link set $netname master br-$vni
    }; done < /evpn_customers.txt
}
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

EvpnFileTemplates['frr_config'] = '''\
ip router-id {routerId}
!
{ospfInterfaces}
!
router bgp {asn}
    no bgp default ipv4-unicast
    neighbor fabric remote-as {asn}
    neighbor fabric update-source {loopbackAddress}
    neighbor fabric capability dynamic
    neighbor fabric capability extended-nexthop
    neighbor fabric graceful-restart
{neighbours}
    !
    address-family l2vpn evpn
        neighbor fabric activate
        neighbor fabric soft-reconfiguration inbound
        advertise-all-vni
        advertise-svi-ip
    exit-address-family
!
'''

EvpnFileTemplates['ospf_interface'] = '''\
interface {interface}
    ip ospf area 0
    ip ospf dead-interval minimal hello-multiplier 2
'''

EvpnFileTemplates['bgp_neighbor'] = '''\
    neighbor {neighbourAddress} peer-group fabric
'''

class Evpn(Layer):
    """!
    @brief The Evpn (Ethernet VPN) layer.

    Work in progress. This layer add supports for BGP-signeled EVPN. 
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
        @param providerRouterNodeName name of the PE router node.
        @param vni VNI.
        '''
        self.__customers.add((providerAsn, customerAsn, customerNetworkName, providerRouterNodeName, vni))

    def getCustomers(self) -> Set[Tuple[int, int, str, str, int]]:
        '''!
        @brief Get set of customers.

        @return set of (provider asn, customer asn, customer netname, pe node name)
        '''
        return self.__customers
    
    def __configureOspf(self, node: Router) -> str:
        self._log('configuring OSPF on as{}/{}'.format(node.getAsn(), node.getName()))

        ospf_ifaces = ''

        for iface in node.getInterfaces():
            net = iface.getNet()
            if net.getType() == NetworkType.InternetExchange: continue
            if not (True in (node.getRole() == NodeRole.Router for node in net.getAssociations())): continue

            ospf_ifaces += EvpnFileTemplates['ospf_interface'].format(
                interface = net.getName()
            )

            net.setMtu(9000)

        return ospf_ifaces

    def __configureIbgpMesh(self, local: Router, nodes: List[Router]) -> str:
        self._log('configuring IBGP mesh on provider edge as{}/{}'.format(local.getAsn(), local.getName()))

        neighbours = ''

        for remote in nodes:
            if local == remote: continue

            neighbours += EvpnFileTemplates['bgp_neighbor'].format(
                neighbourAddress = remote.getLoopbackAddress()
            )

        return neighbours

    def __configureFrr(self, router: Router):
        self._log('setting up FRR on as{}/{}'.format(router.getAsn(), router.getName()))

        router.setFile('/frr_start', EvpnFileTemplates['frr_start_script'])
        router.appendStartCommand('chmod +x /frr_start')
        router.appendStartCommand('/frr_start')
        router.addSoftware('frr')

    def __configureProviderRouter(self, router: Router, peers: List[Router] = []):
        self._log('configuring common properties for provider router as{}/{}'.format(router.getAsn(), router.getName()))

        self.__configureFrr(router)

        router.setFile('/etc/frr/frr.conf', EvpnFileTemplates['frr_config'].format(
            ospfInterfaces = self.__configureOspf(router),
            routerId = router.getLoopbackAddress(),
            asn = router.getAsn(),
            loopbackAddress = router.getLoopbackAddress(),
            neighbours = self.__configureIbgpMesh(router, peers)
        ))

    def __configureProviderEdgeRouter(self, router: Router, customers: List[Tuple[int, str, int]]):
        vxlan_ifaces = ''

        vnis: Set[int] = set()

        for (_, _, vni) in customers: vnis.add(vni)

        self._log('creating vxlan interfaces on as{}/{}'.format(router.getAsn(), router.getName()))
        for vni in vnis:
            vxlan_ifaces += EvpnFileTemplates['vetp_bridge'].format(
                name = vni,
                vni = vni,
                loopbackAddress = router.getLoopbackAddress()
            )

            router.appendStartCommand('ifup br-{}'.format(vni))
            router.appendStartCommand('ifup vtep-{}'.format(vni))
        
        router.setFile('/etc/network/interfaces.d/vxlan_interfaces', vxlan_ifaces)

        # todo: bridge to customer's network

    def __configureAutonomousSystem(self, asn: int, reg: Registry):
        self._log('configuring as{}'.format(asn))

        customers: List[Tuple[int, str, str, int]] = []

        routers: List[Router] = []
        pe: List[Router] = []
        p: List[Router] = []

        for r in ScopedRegistry(str(asn), reg).getByType('rnode'):
            routers.append(r)

        self._log('collecting customers of as{}'.format(asn))
        for (pasn, casn, cn, prn, vni) in self.__customers:
            if pasn != asn: continue
            customers.append((casn, cn, prn, vni))

        self._log('classifying p/pe for as{}'.format(asn))
        for r in routers:
            is_edge = False

            for (_, _, prn, _) in customers:
                if r.getName() == prn:
                    is_edge = True
                    break
            
            if is_edge: pe.append(r)
            else: p.append(r)

        self._log('configuring p routers for as{}'.format(asn))
        for router in p: self.__configureProviderRouter(router)

        self._log('configuring pe routers for as{}'.format(asn))
        for router in pe:
            self._log('collection customers connected to as{}/{}'.format(asn, router.getName()))

            this_customers: List[Tuple[int, str, int]] = []

            for (casn, cn, prn, vni) in customers:
                if prn != router.getName(): continue
                this_customers.append((casn, cn, vni))
            
            self.__configureProviderRouter(router, pe)
            self.__configureProviderEdgeRouter(router, this_customers)

    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()

        asns: Set[int] = set()

        for (asn, _, _, _, _) in self.__customers: asns.add(asn)

        for asn in self.asns:
            if reg.has('seedemu', 'layer', 'Ospf'):
                self._log('Ospf layer exists, masking as{}'.format(asn))
                ospf: Ospf = reg.get('seedemu', 'layer', 'Ospf')
                ospf.maskAsn(asn)

            if reg.has('seedemu', 'layer', 'Ibgp'):
                self._log('Ibgp layer exists, masking as{}'.format(asn))
                ibgp: Ibgp = reg.get('seedemu', 'layer', 'Ibgp')
                ibgp.maskAsn(asn)

            self.__configureAutonomousSystem(asn, reg)

