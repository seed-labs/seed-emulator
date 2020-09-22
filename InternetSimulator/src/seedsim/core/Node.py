from seedsim.SimObject import SimObject
from seedsim.core.Network import NetworkType
from seedsim.core.Interface import Interface
from seedsim.core.enums import NodeRole
from typing import List


class Node(SimObject):
    """!
    @brief Node base class.

    This class represents a generic node.
    """

    _interfaces: List[Interface]

    def __init__(self):
        """!
        @brief Node constructor.
        """
        self._interfaces = []

    def connectNetwork(self, net: Network) -> Interface:
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
        raise NotImplementedError("getRole not implemented.")
        