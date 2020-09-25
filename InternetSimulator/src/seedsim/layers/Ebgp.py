from .Layer import Layer
from seedsim.core import Registry, ScopedRegistry, Network, Node, Interface
from typing import Tuple, List

class Ebgp(Layer):
    """!
    @brief The Ebgp (eBGP) layer.

    This layer enable eBGP peering in InternetExchange.
    """

    __peerings: List[Tuple[int, int, int]]
    __rs_peers: List[Tuple[int, int]]

    def __init__(self):
        """!
        @brief Ebgp layer constructor.
        """
        self.__peerings = []
        self.__rs_peers = []
    
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

    def addRsPeer(self, ix: int, peer: int):
        """!
        @brief Setup RS peering for an AS.

        @param ix IXP id.
        @param peer Participant ASN.

        @throws AssertionError if peering already exist.
        """
        assert (ix, peer) not in self.__rs_peers, '{} already peered with RS at IX{}'.format(peer, ix)

        self.__rs_peers.append((ix, peer))

    def onRender(self) -> None:
        for (ix, peer) in self.__rs_peers:
            ix_reg = ScopedRegistry('ix')
            p_reg = ScopedRegistry(str(peer))

            ix_net: Network = ix_reg.get('net', 'ix{}'.format(ix))
            ix_rs: Node = ix_reg.get('rs', 'ix{}'.format(ix))
            rs_ifs = ix_rs.getInterfaces()
            assert len(rs_ifs) == 1, '??? ix{} rs has {} interfaces.'.format(ix, len(rs_ifs))
            rs_if = rs_ifs[0]

            p_rnodes: List[Node] = p_reg.getByType('rnode')
            p_ixnode: Node = None
            p_ixif: Interface = None
            for node in p_rnodes:
                if p_ixnode != None: break
                for iface in node.getInterfaces():
                    if iface.getNet() == ix_net:
                        p_ixnode = node
                        p_ixif = iface
                        break

            assert p_ixnode != None, 'cannot resolve peering: as{} not in ix{}'.format(a, ix)
            print("===== EbgpLayer: TODO: add to bird.conf: {} as {} (RS) <-> {} as {}".format(rs_if.getAddress(), ix, p_ixif.getAddress(), peer))

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
                    if iface.getNet() == ix_net:
                        b_ixnode = node
                        b_ixif = iface
                        break
            
            assert b_ixnode != None, 'cannot resolve peering: as{} not in ix{}'.format(b, ix)

            print("===== EbgpLayer: TODO: add to bird.conf: {} as {} <-> {} as {}".format(a_ixif.getAddress(), a, b_ixif.getAddress(), b))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EbgpLayer:\n'

        indent += 4
        for (i, a) in self.__rs_peers:
            out += ' ' * indent
            out += 'IX{}: RS <-> AS{}\n'.format(i, a)

        for (i, a, b) in self.__peerings:
            out += ' ' * indent
            out += 'IX{}: AS{} <-> AS{}\n'.format(i, a, b)


        return out

