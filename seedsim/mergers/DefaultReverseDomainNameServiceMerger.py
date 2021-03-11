from .ServiceMerger import ServiceMerger
from seedsim.services import ReverseDomainNameService

class DefaultReverseDomainNameServiceMerger(ServiceMerger):

    def __init__(self, selfVnodePrefix: str, otherVnodePrefix: str) -> None:
        super().__init__(selfVnodePrefix, otherVnodePrefix)

    def getTargetType(self) -> str:
        return 'ReverseDomainNameServiceLayer'

    def _createService(self) -> ReverseDomainNameService:
        return ReverseDomainNameService()