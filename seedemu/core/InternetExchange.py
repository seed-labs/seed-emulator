from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Node import Node,Router
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .Emulator import Emulator
from .Configurable import Configurable
from .Addressing import normalizePrefix
from ipaddress import IPv4Network, IPv6Network

class InternetExchange(Printable, Configurable):
    """!
    @brief InternetExchange class.

    This class represents an internet exchange.
    """

    __id: int
    __net: Network
    __rs: Node
    __name: str

    def __init__(self, id: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None, create_rs = True, rsAddress = None, ipv6Prefix = None, rsIpv6Address = "auto", ipv6PrefixIntent = None):
        """!
        @brief InternetExchange constructor.

        @param id ID (ASN) for the IX.
        @param prefix (optional) prefix to use as peering LAN.
        @param aac (option) AddressAssignmentConstraint to use.
        @param create_rs (optional) create route server node for the IX or not.
          ( route servers are only relevant for BGP, thus the default is True. But RSes can be disabled for SCION)
        @param rsAddress (optional) specific address for the route server. (Required if id > 254)
        """
        if create_rs and id > 254: 
            assert rsAddress != None, "rsAddress can't be None if id > 254"
        self.__id = id

        assert prefix != "auto" or self.__id <= 255, "can't use auto: id > 255"
        network = IPv4Network(prefix) if prefix != "auto" else IPv4Network("10.{}.0.0/24".format(self.__id))
        ipv6_network = None
        if ipv6Prefix is not None:
            ipv6_network = ipv6Prefix if isinstance(ipv6Prefix, IPv6Network) else IPv6Network(normalizePrefix(ipv6Prefix))

        self.__name = 'ix{}'.format(str(self.__id))
        if ipv6PrefixIntent is not None:
            ipv6_intent = ipv6PrefixIntent
        elif ipv6Prefix is None:
            ipv6_intent = None
        else:
            ipv6_intent = "explicit"

        self.__net = Network(self.__name, NetworkType.InternetExchange, network, aac, False, ipv6_network, ipv6_intent)

        if create_rs:
            self.__rs = Router(self.__name, NodeRole.RouteServer, self.__id) 
            if rsAddress == None: 
                self.__rs.joinNetwork(self.__name, ipv6Address=rsIpv6Address)
            else:
                self.__rs.joinNetwork(self.__name, rsAddress, rsIpv6Address)
        else:
            self.__rs = None

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()

        reg.register('ix', 'net', self.__name, self.__net)
        if self.__rs != None:
            reg.register('ix', 'rs', self.__name, self.__rs)
            self.__rs.configure(emulator)

    def getId(self) -> int:
        """!
        @brief Get internet exchange ID.

        @returns ID.
        """
        return self.__id

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
    
    def getNetwork(self) -> Network:
        """!
        @brief Get the network of Internet Exchange.

        @returns Network.
        """

        return self.__net

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'InternetExchange {}:\n'.format(self.__id)

        indent += 4
        out += ' ' * indent
        out += 'Peering LAN Prefix: {}\n'.format(self.__net.getPrefix())
        if self.__net.hasIpv6Prefix():
            out += ' ' * indent
            out += 'Peering LAN IPv6 Prefix: {}\n'.format(self.__net.getIpv6Prefix())

        return out
