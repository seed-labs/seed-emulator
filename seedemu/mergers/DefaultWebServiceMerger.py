from .ServiceMerger import ServiceMerger
from seedemu.services import WebService

class DefaultWebServiceMerger(ServiceMerger):

    def getTargetType(self) -> str:
        return 'WebServiceLayer'

    def _createService(self) -> WebService:
        return WebService()