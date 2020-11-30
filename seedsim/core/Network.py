from ipaddress import IPv4Network, IPv4Address
from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Registry import Registrable
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from typing import Generator, Dict, Tuple, List

class Network(Printable, Registrable):
    """!
    @brief The network class.

    This class represents a network.
    """
    __type: NetworkType
    __prefix: IPv4Network
    __name: str
    __scope: str
    __aac: AddressAssignmentConstraint
    __assigners: Dict[NodeRole, Generator[int, None, None]]

    __connected_nodes: List['Node']

    __d_latency: int       # in ms
    __d_bandwidth: int     # in bps
    __d_drop: float        # percentage

    __mtu: int

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network, aac: AddressAssignmentConstraint = None):
        """!
        @brief Network constructor.

        @param name name of the network. Note that this is considered a "local"
        name. Networks can have the same name, as long as they are in different
        contexts (i.e., different AS).
        @param type type of the network.
        @param prefix prefix of the network.
        @param aac (optional) AddressAssignmentConstraint to use.
        """
        self.__name = name
        self.__type = type
        self.__prefix = prefix
        self.__aac = aac if aac != None else AddressAssignmentConstraint()
        self.__assigners = {}

        self.__connected_nodes = []

        self.__assigners[NodeRole.Router] = self.__aac.getOffsetGenerator(NodeRole.Router)
        self.__assigners[NodeRole.Host] = self.__aac.getOffsetGenerator(NodeRole.Host)

        self.__d_latency = 0
        self.__d_bandwidth = 0
        self.__d_drop = 0

        self.__mtu = 1500

    def setMtu(self, mtu: int):
        """!
        @brief Set MTU of this network.

        @param mtu MTU.
        """
        self.__mtu = mtu

    def getMtu(self) -> int:
        """!
        @brief Get MTU of this network.

        @returns mtu.
        """
        return self.__mtu

    def setDefaultLinkProperties(self, latency: int = 0, bandwidth: int = 0, packetDrop: float = 0):
        """!
        @brief Set default link properties of interfaces attached to the network.

        @param latency (optional) latency to add to the link in ms, default 0. Note that this will be
        apply on all interfaces, meaning the rtt between two hosts will be 2 * latency.
        @param bandwidth (optional) egress bandwidth of the link in bps, 0 for unlimited, default 0.
        @param packetDrop (optional) link packet drop as percentage, 0 for unlimited, default 0.
        """
        assert latency >= 0, 'invalid latency'
        assert bandwidth >= 0, 'invalid bandwidth'
        assert packetDrop >= 0 and packetDrop <= 100, 'invalid packet drop'

        self.__d_latency = latency
        self.__d_bandwidth = bandwidth
        self.__d_drop = packetDrop

    def getDefaultLinkProperties(self) -> Tuple[int, int, int]:
        """!
        @brief Get default link properties.

        @returns tuple (latency, bandwidth, packet drop)
        """
        return (self.__d_latency, self.__d_bandwidth, self.__d_drop)

    def getName(self) -> str:
        """!
        @brief Get name of this network.

        @returns name.
        """
        return self.__name

    def getType(self) -> NetworkType:
        """!
        @brief Get type of this network.

        @returns type.
        """
        return self.__type

    def getPrefix(self) -> IPv4Network:
        """!
        @brief Get prefix of this network.

        @returns prefix.
        """
        return self.__prefix

    def assign(self, nodeRole: NodeRole, asn: int = -1) -> IPv4Address:
        """!
        @brief Assign IP for interface.

        @param nodeRole role of the node getting this assigment.
        @param asn optional. If interface type is InternetExchange, the asn for
        IP address mapping.
        """
        assert not (nodeRole == nodeRole.Host and self.__type == NetworkType.InternetExchange), 'trying to assign IX netwotk to non-router node'

        if self.__type == NetworkType.InternetExchange: return self.__prefix[self.__aac.mapIxAddress(asn)]
        return self.__prefix[next(self.__assigners[nodeRole])]

    def associate(self, node: 'Node'):
        """!
        @brief Associate the node with network.

        @param node node.
        """
        self.__connected_nodes.append(node)

    def getAssociations(self) -> List['Node']:
        """!
        @brief Get list of assoicated nodes.

        @returns list of nodes.
        """
        return self.__connected_nodes

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Network {} ({}):\n'.format(self.__name, self.__type)

        indent += 4
        out += ' ' * indent
        out += 'Prefix: {}\n'.format(self.__prefix)
        out += self.__aac.print(indent)

        return out