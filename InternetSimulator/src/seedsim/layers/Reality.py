from .Layer import Layer
from .Base import AutonomousSystem
from seedsim.core import Node, Network
from typing import List

class Reality(Layer):
    """!
    @brief The Reality.

    Reality Layer provides different ways to connect from and to the real world. 
    """

    def __init__(self):
        """!
        @brief Reality constructor.
        """
    def getName(self):
        return 'Reality'
    
    def getDependencies(self) -> List[str]:
        return ['Base']

    def createRealWorldRouter(self, as: AutonomousSystem, prefixes: List[str] = None) -> Node:
        """!
        @brief add a router node that routes prefixes to the real world.

        @param as AutonomousSystem to add this node to.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        pass

    def createRealWorldAutonomousSystem(self, asn: int, prefixes: List[str] = None) -> AutonomousSystem:
        """!
        @brief add an AutonomousSystem with a router node that routes prefixes
        to the real world.

        @param asn asn.
        @param prefixes (optional) prefixes to annoucne. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS.
        """
        pass

    def enableRealWorldAccess(self, net: Network):
        """!
        @brief Setup VPN server for real-world clients to join a simulated
        network.

        @param net network.
        """
        pass
