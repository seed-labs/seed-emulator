from seedemu.core import Merger
from seedemu.layers import Mpls

class DefaultMplsMerger(Merger):
    """!
    @brief default MPLS layer merging implementation.
    """

    def getName(self) -> str:
        return 'DefaultMplsMerger'

    def getTargetType(self) -> str:
        return 'MplsLayer'

    def doMerge(self, objectA: Mpls, objectB: Mpls) -> Mpls:
        """!
        @brief merge two Mpls layers.

        @param objectA first Mpls layer.
        @param objectB second Mpls layer.
        
        @returns merged Mpls layer.
        """
        new_mpls = Mpls()

        for (asn, nodename) in (objectA.getEdges() | objectB.getEdges()):
            new_mpls.markAsEdge(asn, nodename)

        for asn in (objectA.getEnabled() | objectB.getEnabled()):
            new_mpls.enableOn(asn)

        return new_mpls