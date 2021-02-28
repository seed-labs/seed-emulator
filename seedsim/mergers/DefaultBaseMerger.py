from seedsim.core import Merger, AutonomousSystem
from seedsim.layers import Base
from typing import Dict, Callable

class DefaultBaseMerger(Merger):

    __asConflictHandler: Callable[[AutonomousSystem, AutonomousSystem], AutonomousSystem]

    def __init__(
        self,
        onAsConflict: Callable[[AutonomousSystem, AutonomousSystem], AutonomousSystem] = lambda asA, asB: asA):
        super().__init__()
        self.__asConflictHandler = onAsConflict

    def getName(self) -> str:
        return 'DefaultBaseMerger'

    def getTargetType(self) -> str:
        return 'BaseLayer'

    def doMerge(self, objectA: Base, objectB: Base) -> Base:
        as_objects: Dict[int, AutonomousSystem] = {}

        for asn in objectA.getAsns():
            self._log('found AS{} in the first eumlator.')
            as_objects[asn] = objectA.getAutonomousSystem(asn)

        for asn in objectB.getAsns():
            self._log('found AS{} in the second eumlator.')
            obj = objectB.getAutonomousSystem(asn)
            if asn in as_objects.keys():
                self._log('AS{} is also in the first eumlator, calling conflict handler.')
                obj = self.__asConflictHandler(as_objects[asn], obj)
            if obj != as_objects[asn]: as_objects[asn] = obj
                