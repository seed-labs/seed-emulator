from .Layer import Layer
from seedsim.core import Node

class Mpls(Layer):
    """!
    @brief The Mpls (MPLS) layer.

    This layer is a replacement for the iBGP full mesh setup for the transit
    provider's internal network. Instead of the traditional IP network, which
    requires every hop to have a copy of the full table, MPLS allows non-edge
    hops to hold only the MPLS forwarding table, which negated the need for the
    full table.

    MPLS layer will setup iBGP, LDP, and OSPF. FRRouting will do LDP and OSPF,
    and BIRD will still do BGP. When installed, the MPLS layer will treat all
    nodes with (1) no connection to IX and (2) no connection to a network with
    at least one host node as non-edge nodes and will not put it as part of the
    iBGP mesh network.
    
    The MPLS layer requires kernel modules support. Make sure you load the
    following modules:

    - mpls_router
    - mpls_iptunnel
    - mpls_gso
    """

    def getName(self) -> str:
        return 'Mpls'

    def getDependencies(self) -> List[str]:
        return ['Routing']

    def markAsEdge(self, node: Node):
        """!
        @brief Mark a node as edge node.

        By default, only nodes with connection to IX, or connection to a network
        with at least one host node, will be considered an edge router and be
        included in the iBGP mesh. Use this method to mark a node as edge
        manually.

        @param node node
        """
        pass

