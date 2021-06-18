from __future__ import annotations
from sys import stderr

class Mergeable(object):
    """!
    @brief Mergeable base class
    """

    def getTypeName(self) -> str:
        """!
        @brief Get type name of the current object. 

        @returns type name.
        """
        raise NotImplementedError("getTypeName not implemented.")

    def shouldMerge(self, other: Mergeable) -> bool:
        """!
        @brief Test if two object should be merged, or treated as different
        objects. This is called when merging two object with the same type.
        emulator.

        @param other the other object.

        @returns true if should merge.
        """
        raise NotImplementedError("equals not implemented.")


class Merger(object):
    """!
    @brief Merger base class. 

    When merging, merger are invoked to do the merge.
    """

    def getName(self) -> str:
        """!
        @brief get name of the mergable object.

        @returns name.
        """
        raise NotImplementedError("getName not implemented.")

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

    def _log(self, message):
        print('== {}: {}'.format(self.getName(), message), file=stderr)