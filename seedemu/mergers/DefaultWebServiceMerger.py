from .ServiceMerger import ServiceMerger
from seedemu.services import WebService

class DefaultWebServiceMerger(ServiceMerger):
    """!
    @brief default web service merger implementation.

    This is the default implementation which invokes the default service merger
    to handler merging installation targets.
    """

    def getTargetType(self) -> str:
        return 'WebServiceLayer'

    def _createService(self) -> WebService:
        return WebService()