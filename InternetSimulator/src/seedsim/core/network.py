from ipaddress import IPv4Network
from seedsim.SimObject import SimObject
from seedsim.core.enums import NetworkType
from seedsim.core.AddressAssignmentConstraint import AddressAssignmentConstraint
from typing import Generator

class Network(SimObject):
    """!
    @brief The network class.

    This class represents a network.
    """
    __type: NetworkType
    __prefix: IPv4Network
    __name: str
    __aac: AddressAssignmentConstraint

    __ix_assigner: Generator[int, None, None]
    __router_assigner: Generator[int, None, None]
    __host_assigner: Generator[int, None, None]

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network, aac: AddressAssignmentConstraint = None):
        """!
        @brief Network constructor.

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

    def getName(self) -> str:
        """!
        @brief Get name of this network.

        @returns name.
        """

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

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Network {} ({}):\n'.format(self.__name, self.__type)

        indent += 4
        out += ' ' * indent
        out += 'Prefix: {}\n'.format(self.__prefix)
        out += self.__aac.print(indent)

        return out