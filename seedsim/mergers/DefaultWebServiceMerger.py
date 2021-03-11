from .ServiceMerger import ServiceMerger
from seedsim.services import WebService

class DefaultWebServiceMerger(ServiceMerger):

    def __init__(self, selfVnodePrefix: str, otherVnodePrefix: str) -> None:
        super().__init__(selfVnodePrefix, otherVnodePrefix)

    def getTargetType(self) -> str:
        return 'WebServiceLayer'

    def _createService(self) -> WebService:
        return WebService()