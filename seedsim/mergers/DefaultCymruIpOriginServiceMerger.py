from .ServiceMerger import ServiceMerger
from seedsim.services import CymruIpOriginService

class DefaultCymruIpOriginServiceMerger(ServiceMerger):

    def getName(self) -> str:
        return 'DefaultCymruIpOriginServiceMerger'

    def getTargetType(self) -> str:
        return 'CymruIpOriginServiceLayer'

    def _createService(self) -> CymruIpOriginService:
        return CymruIpOriginService()

    def doMerge(self, objectA: CymruIpOriginService, objectB: CymruIpOriginService) -> CymruIpOriginService:
        new_org: CymruIpOriginService = super().doMerge(objectA, objectB)
        
        for record in (objectA.getRecords() + objectB.getMagetRecordsppings()):
            new_org.addRecord(record)

        return new_org