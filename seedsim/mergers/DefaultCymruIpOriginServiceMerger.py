from seedsim.core import Merger
from seedsim.services import CymruIpOriginService

class DefaultCymruIpOriginServiceMerger(Merger):

    def getName(self) -> str:
        return 'DefaultCymruIpOriginServiceMerger'

    def getTargetType(self) -> str:
        return 'CymruIpOriginServiceLayer'

    def doMerge(self, objectA: CymruIpOriginService, objectB: CymruIpOriginService) -> CymruIpOriginService:
        new_org = CymruIpOriginService()
        for record in (objectA.getRecords() + objectB.getMagetRecordsppings()):
            new_org.addRecord(record)

        return new_org