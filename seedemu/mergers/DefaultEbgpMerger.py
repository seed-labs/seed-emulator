from seedemu.core import Merger
from seedemu.layers import Ebgp, PeerRelationship
from typing import Callable


class DefaultEbgpMerger(Merger):
    """!
    @brief default EBGP layer merging implementation.
    """

    __peeringConflictHandler: Callable[[int, int, int, PeerRelationship, PeerRelationship], PeerRelationship]
    __xcPeeringConflictHandler: Callable[[int, int, int, PeerRelationship, PeerRelationship], PeerRelationship]

    def __init__(
        self,
        onPeeringRelationshipConflict: Callable[[int, int, int, PeerRelationship, PeerRelationship], PeerRelationship] = lambda ix, a, b, relA, relB: relA,
        onXcPeeringRelationshipConflict: Callable[[int, int, PeerRelationship, PeerRelationship], PeerRelationship] = lambda a, b, relA, relB: relA):
        """!
        @brief DefaultEbgpMerger constructor.
        @param onPeeringRelationshipConflict define handler for handling peering
        relationship conflicts. This should be a function that accepts: (ix,
        asnA, asnB, peeringRelationshipA, peeringRelationshipB) and return a
        peering relationship. This defaults to use the peering relationship
        set in the first emulator.
        @param onXcPeeringRelationshipConflict define handler for handling
        peering relationship conflicts. This should be a function that accepts:
        (asnA, asnB, peeringRelationshipA, peeringRelationshipB) and return a
        peering relationship. This defaults to use the peering relationship
        set in the first emulator.
        """
        super().__init__()
        self.__peeringConflictHandler = onPeeringRelationshipConflict
        self.__xcPeeringConflictHandler = onXcPeeringRelationshipConflict
        
    def getName(self) -> str:
        return 'DefaultEbgpMerger'

    def getTargetType(self) -> str:
        return 'EbgpLayer'

    def doMerge(self, objectA: Ebgp, objectB: Ebgp) -> Ebgp:
        """!
        @brief merge two Ebgp layers.

        @param objectA first Ebgp layer.
        @param objectB second Ebgp layer.
        
        @returns merged Ebgp layer.
        """
        
        new_private = objectA.getPrivatePeerings()
        new_rs = objectA.getRsPeers()
        new_xc = objectA.getCrossConnectPeerings()

        for ((ix, a, b), rel) in objectB.getPrivatePeerings().items():
            if (ix, a, b) in new_private.keys() and new_private[(ix, a, b)] != rel:
                self._log('Peering relationship conflict for peering in IX{} between AS{} and AS{}: {} != {}, calling handler'.format(
                    ix, a, b, new_private[(ix, a, b)], rel
                ))
                new_private[(ix, a, b)] = self.__peeringConflictHandler(ix, a, b, new_private[(ix, a, b)], rel)
            else: new_private[(ix, a, b)] = rel
        
        for (ix, asn) in objectB.getRsPeers():
            if (ix, asn) not in new_rs: new_rs.append((ix, asn))

        for ((a, b), rel) in objectB.getCrossConnectPeerings().items():
            if (a, b) in new_xc.keys() and new_private[(a, b)] != rel:
                self._log('Peering relationship conflict for peering in XC between AS{} and AS{}: {} != {}, calling handler'.format(
                    a, b, new_xc[(a, b)], rel
                ))
                new_xc[(a, b)] = self.__xcPeeringConflictHandler(a, b, new_xc[(a, b)], rel)
            else: new_xc[(a, b)] = rel

        new_ebgp = Ebgp()

        for ((ix, a, b), rel) in new_private.items(): new_ebgp.addPrivatePeering(ix, a, b, rel)
        for ((a, b), rel) in new_xc.items(): new_ebgp.addCrossConnectPeering(a, b, rel)
        for (ix, asn) in new_rs: new_ebgp.addRsPeer(ix, asn)

        return new_ebgp