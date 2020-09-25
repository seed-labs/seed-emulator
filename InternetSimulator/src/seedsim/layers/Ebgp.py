from .Layer import Layer
from seedsim.core import Registry, ScopedRegistry, Network, Node, Interface
from typing import Tuple, List

class Ebgp(Layer):
    """!
    @brief The Ebgp (eBGP) layer.

    This layer enable eBGP peering in InternetExchange.
    """

    __peerings: List[Tuple[int, int, int]]

    def __init__(self):
        """!
        @brief Ebgp layer constructor.
        """
        self.__peerings = []
    
    def getName(self) -> str:
        return "Ebgp"

    def getDependencies(self) -> List[str]:
        return ["Routing"]

    def addPrivatePeering(self, ix: int, a: int, b: int):
        """!
        @brief Setup private peering between two ASes in IX.

        @param ix IXP id.
        @param a First ASN.
        @param b Second ASN.

        @throws AssertionError if peering already exist.
        """
        assert (ix, a, b) not in self.__peerings, '{} <-> {} already peered at IX{}'.format(a, b, ix)
        assert (ix, b, a) not in self.__peerings, '{} <-> {} already peered at IX{}'.format(b, a, ix)

        self.__peerings.append((ix, a, b))

    def onRender(self) -> None:
        for (ix, a, b) in self.__peerings:
            ix_reg = ScopedRegistry('ix')
            a_reg = ScopedRegistry(str(a))
            b_reg = ScopedRegistry(str(b))

            ix_net: Network = ix_reg.get('net', 'ix{}'.format(ix))
            a_rnodes: List[Node] = a_reg.getByType('rnode')
            b_rnodes: List[Node] = b_reg.getByType('rnode')

            a_ixnode: Node = None
            a_ixif: Interface = None
            for node in a_rnodes:
                if a_ixnode != None: break
                for iface in node.getInterfaces():
                    ifnet = iface.getNet()
                    if iface.getNet() == ix_net:
                        a_ixnode = node
                        a_ixif = iface
                        break
            
            assert a_ixnode != None, 'cannot resolve peering: as{} not in ix{}'.format(a, ix)

            b_ixnode: Node = None
            b_ixif: Interface = None
            for node in b_rnodes:
                if b_ixnode != None: break
                for iface in node.getInterfaces():
                    ifnet = iface.getNet()
                    if iface.getNet() == ix_net:
                        b_ixnode = node
                        b_ixif = iface
                        break
            
            assert b_ixnode != None, 'cannot resolve peering: as{} not in ix{}'.format(b, ix)

            print("===== EbgpLayer: TODO: Make bird.conf: {} as {} <-> {} as {}".format(a_ixif.getAddress(), a, b_ixif.getAddress(), b))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EbgpLayer:\n'

        indent += 4
        for (i, a, b) in self.__peerings:
            out += ' ' * indent
            out += 'IX{}: AS{} <-> AS{}\n'.format(i, a, b)


        return out

