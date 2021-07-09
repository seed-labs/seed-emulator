from seedemu.core import Merger
from seedemu.layers import Routing

class DefaultRoutingMerger(Merger):
    """!
    @brief default routing layer merger implementation.

    This merger merges direct network lists.
    """

    def getName(self) -> str:
        return 'DefaultRoutingMerger'

    def getTargetType(self) -> str:
        return 'RoutingLayer'

    def doMerge(self, objectA: Routing, objectB: Routing) -> Routing:
        """!
        @brief merge two Routing layers.

        @param objectA first Routing layer.
        @param objectB second Routing layer.
        
        @returns merged Routing layer.
        """
        new_routing = Routing()

        return new_routing