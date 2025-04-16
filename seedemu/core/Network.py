from __future__ import annotations
from ipaddress import IPv4Network, IPv4Address
from .RemoteAccessProvider import RemoteAccessProvider
from .ExternalConnectivityProvider import ExternalConnectivityProvider
from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Registry import Registrable
from .AddressAssignmentConstraint import AddressAssignmentConstraint, Assigner
from .Visualization import Vertex
from .Customizable import Customizable
from .Scope import Scope,NetScope, NetScopeTier, NetScopeType
from typing import Dict, Tuple, List
from .OptionUtil import OptionDomain

class Network(Printable, Registrable, Vertex, Customizable):
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

    __direct: bool

    # these two should be aggregated into a single instance of a common base class ?!
    __rap: RemoteAccessProvider
    __ecp: ExternalConnectivityProvider

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network, aac: AddressAssignmentConstraint = None, direct: bool = False, scope: str = None):
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
        self.__scope = scope

        self.__connected_nodes = []

        ahost =  self.__aac.getOffsetAssigner(NodeRole.Host)
        arouter = self.__aac.getOffsetAssigner(NodeRole.Router)
        self.__assigners[ NodeRole.BorderRouter ] = arouter
        self.__assigners[ NodeRole.Router ] = arouter
        self.__assigners[ NodeRole.Host ] = ahost
        self.__assigners[ NodeRole.ControlService ] = ahost

        self.__direct = direct

        self.__rap = None
        self.__ecp = None

    def scope(self, domain: OptionDomain = None)-> Scope:
        """return a Scope that is specific to this Network"""

        assert domain in [OptionDomain.NET, None], 'input error'
        match (nt:=NetScopeType.from_net(self)):
            case NetScopeType.XC:
                return NetScope(tier=NetScopeTier.Individual,
                        net_type=nt,
                        scope_id=0, # scope of XC nets is None otherwise
                        net_id=self.getName())
            case _:
                return NetScope(tier=NetScopeTier.Individual,
                        net_type=nt,
                        scope_id=int(self.__scope),
                        net_id=self.getName())
    
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
        from .OptionRegistry import OptionRegistry
        self.setOption( OptionRegistry().net_mtu(mtu) )

        return self

    def getMtu(self) -> int:
        """!
        @brief Get MTU of this network.

        @returns mtu.
        """
        return self.getOption('mtu', prefix='net').value

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
        from OptionRegistry import OptionRegistry
        if latency > 0:
            self.setOption(OptionRegistry().net_latency(latency))
        if bandwidth > 0:
            self.setOption(OptionRegistry().net_bandwidth(bandwidth))
        if packetDrop > 0:
            self.setOption(OptionRegistry().net_packetloss(packetDrop))
        return self

    def setType(self, newType: NetworkType) -> Network:
        """!
        @brief overrides network type of this network. Do not use this unless
        you know what you are doing.

        @param newType new net type.

        @returns self, for chaining API calls.
        """
        self.__type = newType

        return self

    def getDefaultLinkProperties(self) -> Tuple[int, int, float]:
        """!
        @brief Get default link properties.

        @returns tuple (latency, bandwidth, packet drop)
        """
        return (self.getOption('latency', prefix='net').value,
                self.getOption('bandwidth', prefix='net').value,
                self.getOption('packetloss', prefix='net').value)

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

    def setHostIpRange(self, hostStart:int , hostEnd: int, hostStep: int):
        """!
        @brief Set IP Range for host nodes

        @param hostStart start address offset of host nodes.
        @param hostEnd end address offset of host nodes.
        @param hostStep end step of host address.
        """

        self.__aac.setHostIpRange(hostStart, hostEnd, hostStep)
        self.__assigners[NodeRole.Host] = self.__aac.getOffsetAssigner(NodeRole.Host)

        return self

    def setDhcpIpRange(self, dhcpStart:int, dhcpEnd: int):
        """!
        @brief Set IP Range for DHCP Server to use

        @param dhcpStart start address offset of dhcp clients.
        @param dhcpEnd end address offset of dhcp clients.
        """
        self.__aac.setDhcpIpRange(dhcpStart, dhcpEnd)
        return self


    def setRouterIpRange(self, routerStart:int, routerEnd:int, routerStep: int):

        """!
        @brief Set IP Range for router nodes

        @param routerStart start address offset of router nodes.
        @param routerEnd end address offset of router nodes.
        @param routerStep end step of router address.
        """

        self.__aac.setRouterIpRange(routerStart, routerEnd, routerStep)
        self.__assigners[NodeRole.Router] = self.__aac.getOffsetAssigner(NodeRole.Router)
        return self

    def getDhcpIpRange(self) -> list:
        """!
        @brief Get IP range for DHCP server to use.
        """
        return self.__aac.getDhcpIpRange()

    def assign(self, nodeRole: NodeRole, asn: int = -1) -> IPv4Address:
        """!
        @brief Assign IP for interface.

        @param nodeRole role of the node getting this assignment.
        @param asn optional. If interface type is InternetExchange, the asn for
        IP address mapping.
        """
        assert not (nodeRole == nodeRole.Host and self.__type == NetworkType.InternetExchange), 'trying to assign IX network to non-router node'

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
        @brief Get list of associated nodes.

        @returns list of nodes.
        """
        return self.__connected_nodes

    def enableRemoteAccess(self, provider: RemoteAccessProvider) -> Network:
        """!
        @brief enable remote access on this network.
                (from outside into the simulation)
        @param provider remote access provider to use.

        @returns self, for chaining API calls.
        """
        assert self.__type == NetworkType.Local, 'remote access can only be enabled on local networks.'
        self.__rap = provider

        return self

    def enableExternalConnectivity(self, provider: ExternalConnectivityProvider) -> Network:
        """
        @brief enable nodes on this emulated network to connect to the 'real' Internet
                (from inside the simulation to the outside)
        """
        assert self.__type == NetworkType.Local, 'external connectivity can only be enabled on local networks.'
        self.__ecp = provider

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

    def getExternalConnectivityProvider(self) -> ExternalConnectivityProvider:
        return self.__ecp

    def getExternalConnectivityProvider(self) -> ExternalConnectivityProvider:
        return self.__ecp

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