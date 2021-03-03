from seedsim.core.Service import Service
from seedsim.core import Merger

class ServiceMerger(Merger):

    def _createService(self) -> Service:
        raise NotImplementedError('_createService not implemented')

    def doMerge(self, objectA: Service, objectB: Service) -> Service:
        new_service = self._createService()

        for t in (objectA.getPendingTargetIps() | objectB.getPendingTargetIps()):
            new_service.__ip_targets.add(t)

        for t in (objectA.getPendingTargetNames() | objectB.getPendingTargetNames()):
            new_service.__name_targets.add(t)

        return new_service