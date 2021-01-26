from .Simulator import SimulatorObject

class Merger(object):
    """!
    @brief Merger class. 

    When merging
    """

    def getTargetType(self) -> str:
        """!
        @brief Get the type name of objects that this merger can handle.

        @returns type name.
        """
        raise NotImplementedError("getTargetType not implemented.")


    def doMerge(self, objectA: SimulatorObject, objectB: SimulatorObject) -> SimulatorObject:
        """!
        @brief Do the merging.

        @param objectA first object.
        @param objectB second object.
        @returns merged object.
        """
        raise NotImplementedError("doMerge not implemented.")
