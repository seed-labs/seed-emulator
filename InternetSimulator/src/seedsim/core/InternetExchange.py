from .Printable import Printable
from .Registry import ScopedRegistry
from .enums import NetworkType, NodeRole
from .Node import Node
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint

class InternetExchange(Printable):
    """!
    @brief InternetExchange class.

    This class represents an internet exchange.
    """

    __id: int
    __reg: ScopedRegistry
    __net: Network
    __rs: Node

    def __init__(self, id: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None):
        """!
        @brief InternetExchange constructor.

        @param id ID (ASN) for the IX.
        """

        self.__id = id
        self.__reg = ScopedRegistry('ix')

        assert prefix != "auto" or self.__id <= 255, "can't use auto: id > 255"
        network = IPv4Network(prefix) if prefix != "auto" else IPv4Network("10.{}.0.0/24".format(self.__id))
        self.__rs = self.__reg.register('rs', str(self.__id), Node(NodeRole.RouteServer, self.__id))
        self.__net = self.__reg.register('net', str(self.__id), Network(str(self.__id), NetworkType.InternetExchange, network, aac))
        rs_node.joinNetwork(self.__net)

    def getPeeringLan(self) -> Network:
        """!
        @brief Get the peering lan network for this IX.

        @returns Peering network.
        """
        return self.__net

    def getRouteServerNode(self) -> Node:
        """!
        @brief Get route server node.

        @returns RS node.
        """
        return self.__rs