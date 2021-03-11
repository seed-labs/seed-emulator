from seedsim.core.Service import Service
from seedsim.core import Merger

class ServiceMerger(Merger):

    __self_prefix: str
    __other_prefix: str

    def __init__(self, selfVnodePrefix: str = '', otherVnodePrefix: str = '') -> None:
        super().__init__()
        self.__self_prefix = selfVnodePrefix
        self.__other_prefix = otherVnodePrefix

    def _createService(self) -> Service:
        raise NotImplementedError('_createService not implemented')

    def doMerge(self, objectA: Service, objectB: Service) -> Service:
        new_service = self._createService()

        new_service.__pending_targets = {}

        for k, v in objectA.getPendingTargets().items(): new_service.__pending_targets['{}{}'.format(self.__self_prefix, k)] = v
        for k, v in objectB.getPendingTargets().items(): new_service.__pending_targets['{}{}'.format(self.__other_prefix, k)] = v

        return new_service