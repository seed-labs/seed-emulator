from seedsim.core import Merger
from seedsim.layers import Ebgp, PeerRelationship
from typing import Callable


class DefaultEbgpMerger(Merger):

    __peeringConflictHandler: Callable[[int, int, int, PeerRelationship, PeerRelationship], PeerRelationship]

    def __init__(
        self,
        onPeeringRelationshipConflict: Callable[[int, int, int, PeerRelationship, PeerRelationship], PeerRelationship] = lambda ix, a, b, relA, relB: relA):
        super().__init__()
        self.__peeringConflictHandler = onPeeringRelationshipConflict
        
    def getName(self) -> str:
        return 'DefaultEbgpMerger'

    def getTargetType(self) -> str:
        return 'EbgpLayer'

    def doMerge(self, objectA: Ebgp, objectB: Ebgp) -> Ebgp:
        new_private = objectA.getPrivatePeerings()
        new_rs = objectA.getRsPeers()

        for ((ix, a, b), rel) in objectB.getPrivatePeerings().items():
            if (ix, a, b) in new_private.keys() and new_private[(ix, a, b)] != rel:
                self._log('Peering relationship conflict for peering in IX{} between AS{} and AS{}: {} != {}, calling handler'.format(
                    ix, a, b, new_private[(ix, a, b)], rel
                ))
                new_private[(ix, a, b)] = self.__peeringConflictHandler(ix, a, b, new_private[(ix, a, b)], rel)
            else: new_private[(ix, a, b)] = rel
        
        for (ix, asn) in objectB.getRsPeers():
            if (ix, asn) not in new_rs: new_rs.append((ix, asn))

        new_ebgp = Ebgp()

        for ((ix, a, b), rel) in new_private: new_ebgp.addPrivatePeering(ix, a, b, rel)
        for (ix, asn) in new_rs: new_ebgp.addRsPeer(ix, asn)

        return new_ebgp