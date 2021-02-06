from .Layer import Layer
from .Base import Base
from .Ospf import Ospf
from seedsim.core import ScopedRegistry, Node, Interface, Graphable, Simulator
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

    This layer automatically setup full mesh peering between routers within AS.
    """
    __masked: Set[int] = set()

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        
        @param simulator simulator.
        """
        self.__masked = set()
        self.addDependency('Ospf', False, False)

    def getName(self) -> str:
        return 'Ibgp'

    def mask(self, asn: int):
        """!
        @brief Mask an AS.

        By default, Ibgp layer will add iBGP peering for all ASes. Use this
        method to mask an AS and disable iBGP.

        @param asn AS to mask.
        """
        self.__masked.add(asn)

    def onRender(self, simulator: Simulator):
        reg = simulator.getRegistry()
        base: Base = reg.get('seedsim', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn), reg).getByType('rnode')

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

    def _doCreateGraphs(self, simulator: Simulator):
        base: Base = simulator.getRegistry().get('seedsim', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue
            asobj = base.getAutonomousSystem(asn)
            asobj.createGraphs(simulator)
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            ibgpgraph = self._addGraph('AS{}: iBGP sessions'.format(asn), False)
            ibgpgraph.copy(l2graph)
            for edge in ibgpgraph.edges:
                edge.style = 'dotted'

            rtrs = ScopedRegistry(str(asn), simulator.getRegistry()).getByType('rnode').copy()
            
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

