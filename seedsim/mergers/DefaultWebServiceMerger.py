from .ServiceMerger import ServiceMerger
from seedsim.services import WebService

class DefaultWebServiceMerger(ServiceMerger):

    def _createService(self) -> WebService:
        return WebService()