from ipaddress import IPv4Network
from seedsim.core.enums import NetworkType

class Network:
    """!
    @brief The network class.

    This class represents a network.
    """
    __type: NetworkType
    __prefix: IPv4Network
    __name: str

    def __init__(self, name: str, type: NetworkType, prefix: IPv4Network):
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