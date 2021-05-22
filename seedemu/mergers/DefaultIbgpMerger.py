from seedemu.core import Merger
from seedemu.layers import Ibgp

class DefaultIbgpMerger(Merger):

    def getName(self) -> str:
        return 'DefaultIbgpMerger'

    def getTargetType(self) -> str:
        return 'IbgpLayer'

    def doMerge(self, objectA: Ibgp, objectB: Ibgp) -> Ibgp:
        new_ibgp = Ibgp()
        for asn in (objectA.getMaskedAsns() | objectB.getMaskedAsns()):
            new_ibgp.maskAsn(asn)

        return new_ibgp