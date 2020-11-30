from .Layer import Layer
from .Base import Base
from .Ospf import Ospf
from seedsim.core import Registry, ScopedRegistry, Node, Interface, Graphable
from seedsim.core.enums import NetworkType
from typing import List, Set, Dict

IbgpFileTemplates: Dict[str, str] = {}

IbgpFileTemplates['ibgp_peer'] = '''
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
'''

class Ibgp(Layer, Graphable):
    """!
    @brief The Ibgp (iBGP) layer.

    @todo bird2

    This layer automatically setup full mesh peering between routers within AS.
    """
    __masked: Set[int] = set()
    __reg = Registry()

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        Graphable.__init__(self)
        self.__masked = set()

    def getName(self) -> str:
        return 'Ibgp'

    def getDependencies(self) -> List[str]:
        return ['Ospf']

    def mask(self, asn: int):
        """!
        @brief Mask an AS.

        By default, Ibgp layer will add iBGP peering for all ASes. Use this
        method to mask an AS and disable iBGP.

        @param asn AS to mask.
        """
        self.__masked.add(asn)

    def __findFirstUnmasked(self, node: Node) -> Interface:
        """!
        @brief find first NIC on the node that is connected to a unmasked
        internal network.

        @param node target node.

        @returns interface if found, None if not found.
        """
        for iface in node.getInterfaces():
            ospf: Ospf = self.__reg.get('seedsim', 'layer', 'Ospf')
            net = iface.getNet()
            if net.getType() == NetworkType.InternetExchange: continue
            if ospf.isMasked(net): continue
            return iface

        return None

    def onRender(self):
        base: Base = self.__reg.get('seedsim', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn)).getByType('rnode')

            for local in routers:
                self._log('setting up IBGP peering on as{}/{}...'.format(asn, local.getName()))

                n = 1
                for remote in routers:
                    if local == remote: continue

                    laddr = local.getLoopbackAddress()
                    raddr = remote.getLoopbackAddress()
                    local.addTable('t_bgp')
                    local.addTablePipe('t_bgp')
                    local.addTablePipe('t_direct', 't_bgp')
                    local.addProtocol('bgp', 'ibgp{}'.format(n), IbgpFileTemplates['ibgp_peer'].format(
                        localAddress = laddr,
                        peerAddress = raddr,
                        asn = asn
                    ))

                    n += 1

                    self._log('adding peering: {} <-> {} (ibgp, as{})'.format(laddr, raddr, asn))

    def _doCreateGraphs(self):
        base: Base = self.__reg.get('seedsim', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue
            asobj = base.getAutonomousSystem(asn)
            asobj.createGraphs()
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            ibgpgraph = self._addGraph('AS{}: iBGP sessions'.format(asn), False)
            ibgpgraph.copy(l2graph)
            for edge in ibgpgraph.edges:
                edge.style = 'dotted'

            rtrs = ScopedRegistry(str(asn)).getByType('rnode').copy()
            
            while len(rtrs) > 0:
                a = rtrs.pop()
                for b in rtrs:
                    ibgpgraph.addEdge('Router: {}'.format(a.getName()), 'Router: {}'.format(b.getName()), style = 'solid')
            

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'IbgpLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'Masked ASes:\n'

        indent += 4
        for asn in self.__masked:
            out += ' ' * indent
            out += '{}\n'.format(asn)

        return out

