from seedemu.core import Merger
from seedemu.layers import Ibgp

class DefaultIbgpMerger(Merger):
    """!
    @brief default IBGP layer merging implementation.
    """

    def getName(self) -> str:
        return 'DefaultIbgpMerger'

    def getTargetType(self) -> str:
        return 'IbgpLayer'

    def doMerge(self, objectA: Ibgp, objectB: Ibgp) -> Ibgp:
        """!
        @brief merge two Ibgp layers.

        @param objectA first Ibgp layer.
        @param objectB second Ibgp layer.
        
        @returns merged Ibgp layer.
        """
        new_ibgp = Ibgp()
        for asn in (objectA.getMaskedAsns() | objectB.getMaskedAsns()):
            new_ibgp.maskAsn(asn)

        return new_ibgp