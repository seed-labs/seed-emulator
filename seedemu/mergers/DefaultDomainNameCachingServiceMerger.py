from .ServiceMerger import ServiceMerger
from seedemu.services import DomainNameCachingService

class DefaultDomainNameCachingServiceMerger(ServiceMerger):
    """!
    @brief default domain name caching service merger implementation.

    This is the default implementation which invokes the default service merger
    to handler merging installation targets, and set auto root to true if any one
    of the inputs have it set to true.
    """

    def _createService(self) -> DomainNameCachingService:
        return DomainNameCachingService()

    def getTargetType(self) -> str:
        return 'DomainNameCachingServiceLayer'

    def doMerge(self, objectA: DomainNameCachingService, objectB: DomainNameCachingService) -> DomainNameCachingService:
        """!
        @brief merge two DomainNameCachingServices.

        @param objectA first DomainNameCachingService.
        @param objectB second DomainNameCachingService.
        
        @returns merged DomainNameCachingService.
        """

        merged: DomainNameCachingService = super().doMerge(objectA, objectB)
        merged.__auto_root = objectA.__auto_root or objectB.__auto_root

        return merged