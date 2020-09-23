from .Printable import Printable
from .Network import Network
from .enums import NodeRole, NetworkType, InterfaceType
from .Registry import ScopedRegistry, Registrable
from typing import List

class File(Printable):
    """!
    @brief File class.

    This class represents a file on a node.
    """

    __content: str
    __path: str

    def __init__(self, path: str, content: str):
        """!
        @brief File constructor.

        Put a file onto a node.

        @param path path of the file.
        @param content content of the file.
        """

    def setPath(self, path: str):
        """!
        @brief Update file path.

        @param path new path.
        """
        self.__path = path

    def setContent(self, content: str):
        """!
        @brief Update file content.

        @param path new path.
        """
        self.__content = content

    def get(self) -> (str, str):
        """!
        @brief Get file path and content.

        @returns a tuple where the first element is path and second element is 
        content
        """
        return (self.__path, self.__content)

class Interface(Printable):
    """!
    @brief Interface class.

    This class represents a network interface card.
    """

    def getType(self) -> InterfaceType:
        """!
        @brief Get type of this interface.

        This will be used in some automation
        cases. For example, AddressAssignmentConstraint will use the node type
        to decide how to assign IP addresses to nodes.

        @returns interface type
        """
        raise NotImplementedError("getType not implemented.")

class Node(Printable, Registrable):
    """!
    @brief Node base class.

    This class represents a generic node.
    """

    __asn: int
    __role: NodeRole
    __reg: ScopedRegistry

    def __init__(self, role: NodeRole, asn: int, scope: str = None):
        """!
        @brief Node constructor.

        @param role role of this node.
        @param asn network that this node belongs to.
        @param scope scope of the node, if not asn.
        """
        self.__interfaces = []
        self.__asn = asn
        self.__reg = ScopedRegistry(scope if scope != None else str(asn))

    def joinNetwork(self, net: Network, address: str = "auto") -> Interface:
        """!
        @brief Connect node to a network.
        """
        pass

    def joinNetworkByName(self, netname: str, address: str = "auto") -> Interface:
        """!
        @brief Connect node to a network.
        """
        pass

    def getRole(self) -> NodeRole:
        """!
        @brief Get role of current node.

        Get role type of current node. 

        @returns role.
        """
        return this.__role

    def getFile(self, path: str) -> File:
        """!
        @brief Get a file object, and create if not exist.

        @param path file path.
        """
        pass

    def setFile(self, path: str, content: str):
        """!
        @brief Set content of the file.

        @param path path of the file. Will be created if not exist, and will be
        override if already exist.
        @param content file content.
        """
        pass

    def appendFile(self, path: str, content: str):
        """!
        @brief Append content to a file.

        @param path path of the file. Will be created if not exist.
        @param content content to append.
        """
        pass
        