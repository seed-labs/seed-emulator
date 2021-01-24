from .Printable import Printable
from .Registry import ScopedRegistry
from .enums import NetworkType, NodeRole
from .Node import Node, Interface
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from ipaddress import IPv4Network

class InternetExchange(Printable):
    """!
    @brief InternetExchange class.

    This class represents an internet exchange.
    """

    __id: int
    __reg: ScopedRegistry
    __net: Network
    __rs: Node
    __rsif: Interface

    def __init__(self, id: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None):
        """!
        @brief InternetExchange constructor.

        @param id ID (ASN) for the IX.
        @param prefix (optional) prefix to use as peering LAN.
        @param aac (option) AddressAssignmentConstraint to use.
        """

        self.__id = id
        self.__reg = ScopedRegistry('ix')

        assert prefix != "auto" or self.__id <= 255, "can't use auto: id > 255"
        network = IPv4Network(prefix) if prefix != "auto" else IPv4Network("10.{}.0.0/24".format(self.__id))
        name = 'ix{}'.format(str(self.__id))
        self.__rs = self.__reg.register('rs', name, Node(name, NodeRole.RouteServer, self.__id))
        self.__net = self.__reg.register('net', name, Network(name, NetworkType.InternetExchange, network, aac))
        self.__rsif = self.__rs.joinNetwork(self.__net)

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

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'InternetExchange {}:\n'.format(self.__id)

        indent += 4
        out += ' ' * indent
        out += 'Peering LAN Prefix: {}\n'.format(self.__net.getPrefix())

        out += ' ' * indent
        out += 'RS Address: {}\n'.format(self.__rsif.getAddress())

        return out