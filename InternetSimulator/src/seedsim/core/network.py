from ipaddress import IPv4Network
from .enums import NetworkType

class Network:
    """!
    @brief The network class.

    This class represents a network.
    """
    __type: NetworkType
    __prefix: IPv4Network

    def __init__(self, type: NetworkType, prefix: IPv4Network):
        """!
        @brief Network constructor.

        @param type type of the network.
        @param prefix prefix of the network.
        """
        self.__type = type
        self.__prefix = prefix

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