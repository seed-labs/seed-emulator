from .ServiceMerger import ServiceMerger
from seedsim.services import WebService

class DefaultWebServiceMerger(ServiceMerger):

    def _createService(self) -> WebService:
        return WebService()

    def doMerge(self, objectA: WebService, objectB: WebService) -> WebService:
        return super().doMerge(objectA, objectB)