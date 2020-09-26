from ipaddress import IPv4Network, IPv4Address
from .Printable import Printable
from .enums import NetworkType, NodeRole
from .Registry import Registrable
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from typing import Generator, Dict

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

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network, aac: AddressAssignmentConstraint = None):
        """!
        @brief Network constructor.

        @param scope scope of the network.
        @param name name of the network. Note that this is considered a "local"
        name. Networks can have the same name, as long as they are in different
        contexts (i.e., different AS).
        @param type type of the network.
        @param prefix prefix of the network.
        """
        self.__name = name
        self.__type = type
        self.__prefix = prefix
        self.__aac = aac if aac != None else AddressAssignmentConstraint()
        self.__assigners = {}

        self.__assigners[NodeRole.Router] = self.__aac.getOffsetGenerator(NodeRole.Router)
        self.__assigners[NodeRole.Host] = self.__aac.getOffsetGenerator(NodeRole.Host)

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


    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Network {} ({}):\n'.format(self.__name, self.__type)

        indent += 4
        out += ' ' * indent
        out += 'Prefix: {}\n'.format(self.__prefix)
        out += self.__aac.print(indent)

        return out