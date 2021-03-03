from seedsim.core import Merger
from seedsim.layers import Routing

class DefaultRoutingMerger(Merger):

    def getName(self) -> str:
        return 'DefaultRoutingMerger'

    def getTargetType(self) -> str:
        return 'RoutingLayer'

    def doMerge(self, objectA: Routing, objectB: Routing) -> Routing:
        new_routing = Routing()
        for (asn, net) in (objectA.getDirects() | objectB.getDirects()):
            new_routing.addDirect(asn, net)

        return new_routing