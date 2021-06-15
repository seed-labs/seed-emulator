from seedemu.core.Service import Service
from seedemu.core import Merger

class ServiceMerger(Merger):
    """!
    @brief Merger that handles merging installation targets.
    """

    def _createService(self) -> Service:
        """!
        @brief create a new services instance of the service to be merged.

        @returns service instance.
        """

        raise NotImplementedError('_createService not implemented')

    def doMerge(self, objectA: Service, objectB: Service) -> Service:
        """!
        @brief merge installation targets.

        @param objectA first service instance.
        @param objectB second service instance.

        @returns merged services.
        """

        assert objectA.getName() == objectB.getName(), 'cannot merge different services.'

        new_service = self._createService()

        new_service.setPendingTargets(dict(objectA.getPendingTargets(), **objectB.getPendingTargets()))

        return new_service