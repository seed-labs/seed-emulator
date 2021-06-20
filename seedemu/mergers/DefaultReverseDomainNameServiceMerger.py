from .ServiceMerger import ServiceMerger
from seedemu.services import ReverseDomainNameService

class DefaultReverseDomainNameServiceMerger(ServiceMerger):
    """!
    @brief default reverse domain name service merger implementation.

    This is the defualt implementation which invokes the default service merger
    to handler merging installation targets.
    """

    def getTargetType(self) -> str:
        return 'ReverseDomainNameServiceLayer'

    def _createService(self) -> ReverseDomainNameService:
        return ReverseDomainNameService()