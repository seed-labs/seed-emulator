from .Printable import Printable
from .Network import Network
from .Interface import Interface
from .File import File
from .enums import NodeRole, NetworkType
from typing import List


class Node(Printable):
    """!
    @brief Node base class.

    This class represents a generic node.
    """

    _interfaces: List[Interface]
    __files: List[File]
    __role: NodeRole

    def __init__(self, role: NodeRole):
        """!
        @brief Node constructor.

        @param role role of this node.
        """
        self.__interfaces = []

    def connectNetwork(self, net: Network, address: str = "auto") -> Interface:
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
        