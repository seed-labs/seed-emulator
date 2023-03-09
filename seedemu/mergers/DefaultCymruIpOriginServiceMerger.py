from .ServiceMerger import ServiceMerger
from seedemu.services import CymruIpOriginService

class DefaultCymruIpOriginServiceMerger(ServiceMerger):
    """!
    @brief default IP origin service merger implementation.

    This is the default implementation which invokes the default service merger
    to handler merging installation targets, and merge manually created records.
    """

    def getName(self) -> str:
        return 'DefaultCymruIpOriginServiceMerger'

    def getTargetType(self) -> str:
        return 'CymruIpOriginServiceLayer'

    def _createService(self) -> CymruIpOriginService:
        return CymruIpOriginService()

    def doMerge(self, objectA: CymruIpOriginService, objectB: CymruIpOriginService) -> CymruIpOriginService:
        """!
        @brief merge two IP origin services.

        @param objectA first IP origin service.
        @param objectB second IP origin service.

        @returns merged IP origin service.
        """

        new_org: CymruIpOriginService = super().doMerge(objectA, objectB)
        
        for record in (objectA.getRecords() + objectB.getRecords()):
            new_org.addRecord(record)

        return new_org