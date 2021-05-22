from .ServiceMerger import ServiceMerger
from seedemu.services import ReverseDomainNameService

class DefaultReverseDomainNameServiceMerger(ServiceMerger):

    def getTargetType(self) -> str:
        return 'ReverseDomainNameServiceLayer'

    def _createService(self) -> ReverseDomainNameService:
        return ReverseDomainNameService()