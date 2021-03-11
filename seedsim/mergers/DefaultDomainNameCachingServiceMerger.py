from .ServiceMerger import ServiceMerger
from seedsim.services import DomainNameCachingService

class DefaultDomainNameCachingServiceMerger(ServiceMerger):

    def _createService(self) -> DomainNameCachingService:
        return DomainNameCachingService()

    def getTargetType(self) -> str:
        return 'DomainNameCachingServiceLayer'

    def doMerge(self, objectA: DomainNameCachingService, objectB: DomainNameCachingService) -> DomainNameCachingService:
        merged: DomainNameCachingService = super().doMerge(objectA, objectB)
        merged.__auto_root = objectA.__auto_root or objectB.__auto_root

        return merged