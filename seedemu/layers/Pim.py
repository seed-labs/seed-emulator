from __future__ import annotations
from .Ospf import Ospf
from .Ibgp import Ibgp
from .Routing import Router
from seedemu.core import Node, ScopedRegistry, Graphable, Emulator, Layer
from seedemu.core.enums import NetworkType, NodeRole
from typing import List, Tuple, Dict, Set

FileTemplates: Dict[str, str] = {}

FileTemplates['frr_start_script'] = """\
#!/bin/bash
mount -o remount rw /proc/sys 2> /dev/null
#echo '1048575' > /proc/sys/net/mpls/platform_labels
# while read -r iface; do echo '1' > "/proc/sys/net/mpls/conf/$iface/input"; done < mpls_ifaces.txt
sed -i 's/pimd=no/pimd=yes/' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
service frr start
"""

FileTemplates['frr_config'] = """\
router-id {loopbackAddress}
{ospfInterfaces}

{pimInterfaces}
log file /var/log/frr/frr.log
debug igmp
debug pim
debug pim zebra
ip pim rp 10.{asn}.0.254 224.0.0.0/4

! You may want to enable ssmpingd for troubleshooting
! See http://www.venaas.no/multicast/ssmping/
!
!ip ssmpingd 1.1.1.1

router ospf
 redistribute connected
"""



"""
! HINTS:
!  - Enable "ip pim ssm" on the interface directly attached to the
!    multicast source host (if this is the first-hop router)
!  - Enable "ip pim ssm" on pim-routers-facing interfaces
!  - Enable "ip igmp" on IGMPv3-hosts-facing interfaces
!  - In order to inject IGMPv3 local membership information in the
!    PIM protocol state, enable both "ip pim ssm" and "ip igmp" on
!    the same interface; otherwise PIM won't advertise
!    IGMPv3-learned membership to other PIM routers

interface eth0
 ip pim ssm
 ip igmp
"""

FileTemplates['frr_config_pim_iface'] = """\
  interface {interface}
  ip pim ssm
  ip igmp
"""

# todo: make configurable hello/dead
FileTemplates['frr_config_ospf_iface'] = """\
interface {interface}
 ip ospf area 0
 ip ospf dead-interval minimal hello-multiplier 2
"""


class Pim(Layer):
    """!
    @brief The Pim (PIM) layer.
    """
    __enabled: Set[int]

    def __init__(self):
        """!
        @brief layer constructor.
        """
        super().__init__()
        self.__enabled = set()

        # they are not really "dependency," we just need them to render after
        # us, in case we need to setup masks.
        self.addDependency('Ospf', True, True)
        
        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return 'Pim'

    def enableOn(self, asn: int) -> Pim:
        """!
        @brief configure PIM multicast in an AS.

        It is not enabled by default. 
        This also automatically setup masks for OSPF layer if they exist.

        @param asn ASN.

        @returns self, for chaining API calls.
        """
        self.__enabled.add(asn)

        return self

    def getEnabled(self) -> Set[int]:
        """!
        @brief Get set of ASNs that have PIM enabled.

        @return set of ASNs
        """
        return self.__enabled


    def __setUpPimOspf(self, node: Router):
        """!
        @brief Setup PIM and OSPF on router.

        @param node node.
        """
        self._log('Setting up PIM and OSPF on as{}/{}'.format(node.getAsn(), node.getName()))

        node.setPrivileged(True)
        node.addSoftware('frr')

        ospf_ifaces = ''
        pim_ifaces = ''
        
        for iface in node.getInterfaces():
            net = iface.getNet()
            if net.getType() == NetworkType.InternetExchange: continue
            pim_ifaces += FileTemplates['frr_config_pim_iface'].format(interface = net.getName())
            # is there at least one other router on this net ?
            if not (True in (node.getRole() == NodeRole.Router or node.getRole() == NodeRole.BorderRouter for node in net.getAssociations())): continue
            ospf_ifaces += FileTemplates['frr_config_ospf_iface'].format(interface = net.getName())                       

        node.setFile('/etc/frr/frr.conf', FileTemplates['frr_config'].format(
            loopbackAddress = node.getLoopbackAddress(),
            ospfInterfaces = ospf_ifaces,
            asn = node.getAsn(),
            pimInterfaces = pim_ifaces
        ))

        node.setFile('/frr_start', FileTemplates['frr_start_script'])        
        node.appendStartCommand('chmod +x /frr_start')
        node.appendStartCommand('/frr_start')


    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for asn in self.__enabled:
            if reg.has('seedemu', 'layer', 'Ospf'):
                self._log('Ospf layer exists, masking as{}'.format(asn))
                ospf: Ospf = reg.get('seedemu', 'layer', 'Ospf')
                ospf.maskAsn(asn)


            scope = ScopedRegistry(str(asn), reg)
            nodes = scope.getByType('rnode')    
            hnodes = scope.getByType('hnode')
            for h in hnodes: h.addSoftware('iperf ssmping') #mcjoin omping mcsender 
            
            for n in nodes: self.__setUpPimOspf(n)
            

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'PIMLayer:\n'
        
        indent += 4
        out += ' ' * indent
        out += 'Enabled on:\n'

        indent += 4
        for asn in self.__enabled:
            out += ' ' * indent
            out += 'as{}\n'.format(asn)

        return out
            