from .ServiceMerger import ServiceMerger
from seedemu.services import BgpLookingGlassService

class DefaultBgpLookingGlassServiceMerger(ServiceMerger):

    def getTargetType(self) -> str:
        return 'BgpLookingGlassServiceLayer'

    def _createService(self) -> BgpLookingGlassService:
        return BgpLookingGlassService()
