from seedsim.core import Merger
from seedsim.layers import Dnssec

class DefaultDnssecMerger(Merger):

    def getName(self) -> str:
        return 'DefaultDnssecMerger'

    def getTargetType(self) -> str:
        return 'DnssecLayer'

    def doMerge(self, objectA: Dnssec, objectB: Dnssec) -> Dnssec:
        new_dnssec = Dnssec()
        for zone in (objectA.getEnabledZones() | objectB.getEnabledZones()):
            new_dnssec.enableOn(zone)

        return new_dnssec