from seedemu.core import Merger
from seedemu.layers import Ospf

class DefaultOspfMerger(Merger):
    """!
    @brief default OSPF layer merging implementation.
    """

    def getName(self) -> str:
        return 'DefaultOspfMerger'

    def getTargetType(self) -> str:
        return 'OspfLayer'

    def doMerge(self, objectA: Ospf, objectB: Ospf) -> Ospf:
        new_ospf = Ospf()

        for (asn, netname) in (objectA.getStubs() | objectB.getStubs()):
            new_ospf.markAsStub(asn, netname)

        for (asn, netname) in (objectA.getMaskedNetworks() | objectB.getMaskedNetworks()):
            new_ospf.maskNetwork(asn, netname)

        for asn in (objectA.getMaskedAsns() | objectB.getMaskedAsns()):
            new_ospf.maskAsn(asn)

        return new_ospf