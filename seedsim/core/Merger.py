class Mergeable(object):
    """!
    @brief Mergeable base class
    """

    def getTypeName(self) -> str:
        """!
        @brief Get type name of the current object. 
        """
        raise NotImplementedError("getTypeName not implemented.")

    def shouldMerge(self, other: Mergeable) -> bool:
        """!
        @brief Test if two object should be merged, or treated as different
        objects. This is called when merging two object with the same type.
        simulator.

        @param other the other object
        """
        raise NotImplementedError("equals not implemented.")


class Merger(object):
    """!
    @brief Merger base class. 

    When merging
    """

    def getTargetType(self) -> str:
        """!
        @brief Get the type name of objects that this merger can handle.

        @returns type name.
        """
        raise NotImplementedError("getTargetType not implemented.")


    def doMerge(self, objectA: Mergeable, objectB: Mergeable) -> Mergeable:
        """!
        @brief Do merging.

        @param objectA first object.
        @param objectB second object.
        @returns merged object.
        """
        raise NotImplementedError("doMerge not implemented.")
