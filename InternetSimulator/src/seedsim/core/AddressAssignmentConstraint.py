from seedsim.SimObject import SimObject
from seedsim.core.enums import InterfaceType
from typing import Generator

class AddressAssignmentConstraint(SimObject):
    """!
    AddressAssignmentConstraint class.

    This class defines how IP addresses should be assign to network interfaces.
    Derive from this class to change the default behavior.
    """

    def __range(self, a: int, b: int):
        for n in range(a, b): yield n

    def __always(self, a: int):
        while True: yield a

    def getOffsetGenerator(self, type: InterfaceType, asn: int = 0) -> Generator[int, None, None]:
        """!
        @brief Get IP offset generator for a type of interface.

        @todo Handle pure-internal routers.

        @param type type of interface.
        @param asn optional. ASN of this node.
        @returns An int generator that generates IP address offset.
        @throws  AssertionError if asn is invalud for the IX type port.
        """

        if role == InterfaceType.Host: return self.__range(71, 99)
        if role == InterfaceType.Internal: return self.__range(254, 200)
        if role == InterfaceType.Ix:
            assert asn > 1, "defualt offset generator for IX needs asn to be > 1"
            return self.__always(asn)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'AddressAssignmentConstraint: Default Constraint\n'

        return out