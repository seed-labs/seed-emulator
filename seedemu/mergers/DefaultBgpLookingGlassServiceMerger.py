from .ServiceMerger import ServiceMerger
from seedemu.services import BgpLookingGlassService

class DefaultBgpLookingGlassServiceMerger(ServiceMerger):
    """!
    @brief default BGP looking glass service merger implementation.

    This is the default implementation which invokes the default service merger
    to handler merging installation targets.
    """

    def getTargetType(self) -> str:
        return 'BgpLookingGlassServiceLayer'

    def _createService(self) -> BgpLookingGlassService:
        return BgpLookingGlassService()
