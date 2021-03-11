from seedsim.core.Service import Service
from seedsim.core import Merger

class ServiceMerger(Merger):

    def _createService(self) -> Service:
        raise NotImplementedError('_createService not implemented')

    def doMerge(self, objectA: Service, objectB: Service) -> Service:
        new_service = self._createService()

        new_service.setPendingTargets(dict(objectA.getPendingTargets(), **objectB.getPendingTargets()))

        return new_service