from .ServiceMerger import ServiceMerger
from seedsim.services import ReverseDomainNameService

class DefaultReverseDomainNameServiceMerger(ServiceMerger):

    def _createService(self) -> ReverseDomainNameService:
        return ReverseDomainNameService()