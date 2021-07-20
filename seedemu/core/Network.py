from __future__ import annotations
from ipaddress import IPv4Network, IPv4Address
from .RemoteAccessProvider import RemoteAccessProvider
from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Registry import Registrable
from .AddressAssignmentConstraint import AddressAssignmentConstraint, Assigner
from .Visualization import Vertex
from typing import Dict, Tuple, List

class Network(Printable, Registrable, Vertex):
    """!
    @brief The network class.

    This class represents a network.
    """
    __type: NetworkType
    __prefix: IPv4Network
    __name: str
    __scope: str
    __aac: AddressAssignmentConstraint
    __assigners: Dict[NodeRole, Assigner]

    __connected_nodes: List['Node']

    __d_latency: int       # in ms
    __d_bandwidth: int     # in bps
    __d_drop: float        # percentage

    __mtu: int

    __direct: bool

    __rap: RemoteAccessProvider

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network, aac: AddressAssignmentConstraint = None, direct: bool = False):
        """!
        @brief Network constructor.

        @param name name of the network. Note that this is considered a "local"
        name. Networks can have the same name, as long as they are in different
        contexts (i.e., different AS).
        @param type type of the network.
        @param prefix prefix of the network.
        @param aac (optional) AddressAssignmentConstraint to use.
        @param direct (optional) mark network as direct. A direct network will be
        loaded to RIB by routing layer. Default to False.
        """
        super().__init__()

        self.__name = name
        self.__type = type
        self.__prefix = prefix
        self.__aac = aac if aac != None else AddressAssignmentConstraint()
        self.__assigners = {}

        self.__connected_nodes = []

        self.__assigners[NodeRole.Router] = self.__aac.getOffsetAssigner(NodeRole.Router)
        self.__assigners[NodeRole.Host] = self.__aac.getOffsetAssigner(NodeRole.Host)

        self.__d_latency = 0
        self.__d_bandwidth = 0
        self.__d_drop = 0

        self.__mtu = 1500

        self.__direct = direct

        self.__rap = None

    def isDirect(self) -> bool:
        """!
        @brief test if this network is direct network. A direct network will be
        added to RIB of routing daemons.

        @returns true if direct, false otherwise.
        """

        return self.__direct

    def setDirect(self, direct: bool) -> Network:
        """!
        @brief set if this network is direct network. A direct network will be
        added to RIB of routing daemons.

        @param direct bool, true to set the network as direct, false otherwise.

        @returns self, for chaining API calls.
        """

        self.__direct = direct

        return self

    def setMtu(self, mtu: int) -> Network:
        """!
        @brief Set MTU of this network.

        @param mtu MTU.

        @returns self, for chaining API calls.
        """
        self.__mtu = mtu

        return self

    def getMtu(self) -> int:
        """!
        @brief Get MTU of this network.

        @returns mtu.
        """
        return self.__mtu

    def setDefaultLinkProperties(self, latency: int = 0, bandwidth: int = 0, packetDrop: float = 0) -> Network:
        """!
        @brief Set default link properties of interfaces attached to the network.

        @param latency (optional) latency to add to the link in ms, default 0. Note that this will be
        apply on all interfaces, meaning the rtt between two hosts will be 2 * latency.
        @param bandwidth (optional) egress bandwidth of the link in bps, 0 for unlimited, default 0.
        @param packetDrop (optional) link packet drop as percentage, 0 for unlimited, default 0.

        @returns self, for chaining API calls.
        """
        assert latency >= 0, 'invalid latency'
        assert bandwidth >= 0, 'invalid bandwidth'
        assert packetDrop >= 0 and packetDrop <= 100, 'invalid packet drop'

        self.__d_latency = latency
        self.__d_bandwidth = bandwidth
        self.__d_drop = packetDrop

        return self

    def setType(self, newType: NetworkType) -> Network:
        """!
        @brief overrides network type of this network. Do not use this unless
        you know what you are doring.

        @param newType new nettype.

        @returns self, for chaining API calls.
        """
        self.__type = newType

        return self

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
        return self.__prefix[self.__assigners[nodeRole].next()]

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

    def enableRemoteAccess(self, provider: RemoteAccessProvider) -> Network:
        """!
        @brief enable remote access on this netowrk.

        @param provider remote access provider to use.

        @returns self, for chaining API calls.
        """
        assert self.__type == NetworkType.Local, 'remote access can only be enabled on local networks.'
        self.__rap = provider

        return self

    def disableRemoteAccess(self) -> Network:
        """!
        @brief disable remote access on this network.

        @returns self, for chaining API calls.
        """
        self.__rap = None

        return self

    def getRemoteAccessProvider(self) -> RemoteAccessProvider:
        """!
        @brief get the remote access provider for this network.

        @returns RAP, or None.
        """
        return self.__rap

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Network {} ({}):\n'.format(self.__name, self.__type)

        indent += 4
        out += ' ' * indent
        out += 'Prefix: {}\n'.format(self.__prefix)
        out += self.__aac.print(indent)

        if self.__rap != None:
            indent += 4
            out += ' ' * indent
            out += 'Remote access provider: {}\n'.format(self.__rap.getName())

        return out