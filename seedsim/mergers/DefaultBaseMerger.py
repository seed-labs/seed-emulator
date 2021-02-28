from seedsim.core import Merger, AutonomousSystem, InternetExchange
from seedsim.layers import Base
from typing import Dict, Callable

class DefaultBaseMerger(Merger):

    __asConflictHandler: Callable[[AutonomousSystem, AutonomousSystem], AutonomousSystem]
    __ixConflictHandler: Callable[[InternetExchange, InternetExchange], InternetExchange]

    def __init__(
        self,
        onAsConflict: Callable[[AutonomousSystem, AutonomousSystem], AutonomousSystem] = lambda asA, asB: asA,
        onIxConflict: Callable[[InternetExchange, InternetExchange], InternetExchange] = lambda ixA, ixB: ixA):
        super().__init__()
        self.__asConflictHandler = onAsConflict
        self.__ixConflictHandler = onIxConflict

    def getName(self) -> str:
        return 'DefaultBaseMerger'

    def getTargetType(self) -> str:
        return 'BaseLayer'

    def doMerge(self, objectA: Base, objectB: Base) -> Base:
        as_objects: Dict[int, AutonomousSystem] = {}
        ix_objects: Dict[int, InternetExchange] = {}

        for asn in objectA.getAsns():
            self._log('found AS{} in the first eumlator.'.format(asn))
            as_objects[asn] = objectA.getAutonomousSystem(asn)

        for ix in objectA.getInternetExchangeIds():
            self._log('found IX{} in the first eumlator.'.format(ix))
            ix_objects[ix] = objectA.getInternetExchange(ix)

        for asn in objectB.getAsns():
            self._log('found AS{} in the second eumlator.'.format(asn))
            obj = objectB.getAutonomousSystem(asn)
            if asn in as_objects.keys():
                self._log('AS{} is also in the first eumlator, calling conflict handler.'.format(asn))
                obj = self.__asConflictHandler(as_objects[asn], obj)
            if obj != as_objects[asn]: as_objects[asn] = obj
        
        for ix in objectB.getInternetExchangeIds():
            self._log('found IX{} in the second eumlator.'.format(ix))
            obj = objectB.getInternetExchange(ix)
            if ix in ix_objects.keys():
                self._log('IX{} is also in the first eumlator, calling conflict handler.'.format(ix))
                obj = self.__ixConflictHandler(ix_objects[ix], obj)
            if obj != ix_objects[ix]: ix_objects[ix] = obj

        new_base = Base()

        for ix_object in ix_objects.values(): new_base.setInternetExchange(ix_object)
        for as_object in as_objects.values(): new_base.setAutonomousSystem(as_object)

        return new_base