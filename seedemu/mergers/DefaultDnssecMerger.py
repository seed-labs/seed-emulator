from seedemu.core import Merger
from seedemu.layers import Dnssec

class DefaultDnssecMerger(Merger):
    """!
    @brief default DNSSEC layer merger implementation.

    This merger merges zone names with DNSSEC enabled.
    """

    def getName(self) -> str:
        return 'DefaultDnssecMerger'

    def getTargetType(self) -> str:
        return 'DnssecLayer'

    def doMerge(self, objectA: Dnssec, objectB: Dnssec) -> Dnssec:
        """!
        @brief perform Dnssec layer merge.

        @param objectA first Dnssec layer.
        @param objectB second Dnssec layer.

        @returns merged Dnssec layer.
        """

        new_dnssec = Dnssec()
        for zone in (objectA.getEnabledZones() | objectB.getEnabledZones()):
            new_dnssec.enableOn(zone)

        return new_dnssec