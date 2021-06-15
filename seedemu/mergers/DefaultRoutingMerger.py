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
        new_routing = Routing()
        for (asn, net) in (objectA.getDirects() | objectB.getDirects()):
            new_routing.addDirect(asn, net)

        return new_routing