from .Printable import Printable
from .enums import NetworkType, NodeRole
from typing import Generator

class AddressAssignmentConstraint(Printable):
    """!
    AddressAssignmentConstraint class.

    This class defines how IP addresses should be assign to network interfaces.
    Derive from this class to change the default behavior.
    """

    def __range(self, a: int, b: int, s: int = 1):
        for n in range(a, b, s): yield n

    def __always(self, a: int):
        while True: yield a

    def getOffsetGenerator(self, type: NodeRole) -> Generator[int, None, None]:
        """!
        @brief Get IP offset generator for a type of node.

        @todo Handle pure-internal routers.

        @param type type of the node.
        @returns An int generator that generates IP address offset.
        @throws ValueError if try to get generator of IX interface.
        """

        if type == NodeRole.Host: return self.__range(71, 99)
        if type == NodeRole.Router: return self.__range(254, 200, -1)

        raise ValueError("IX IP assigment must done with mapIxAddress().")

    def mapIxAddress(self, asn: int) -> int:
        """!
        @brief Map ASN to IP address in IX peering LAN.

        @param asn ASN of IX participant.
        @returns offset.
        @throws AssertionError if can't map ASN to IP address.
        """
        assert asn >= 2 and asn <= 254, "can't map ASN {} to IX address.".format(asn)
        return asn

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'AddressAssignmentConstraint: Default Constraint\n'

        return out