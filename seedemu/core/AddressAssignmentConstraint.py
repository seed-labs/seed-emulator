from .Printable import Printable
from .enums import NodeRole

class Assigner:
    """!
    @brief Default address assigner.

    This replaces python's generator, as that cannot be dumped.
    """

    __current: int
    __end: int
    __step: int

    def __init__(self, start: int, end: int, step: int):
        """!
        @brief create a new assigner
        
        @param start start
        @param end end
        @param step step
        """
        self.__current = start
        self.__end = end
        self.__step = step

    def next(self) -> int:
        """!
        @brief get next.

        @returns next value.
        """
        if self.__step > 0 and self.__current > self.__end:
            assert False, 'out of range.'
        if self.__step < 0 and self.__current < self.__end:
            assert False, 'out of range.'
        v = self.__current
        self.__current += self.__step
        return v

class AddressAssignmentConstraint(Printable):
    """!
    AddressAssignmentConstraint class.

    This class defines how IP addresses should be assign to network interfaces.
    Derive from this class to change the default behavior.
    """

    __hostStart: int
    __hostEnd: int
    __routerStart: int
    __routerEnd: int
    __hostStep: int
    __routerStep: int


    def __init__(self, hostStart: int = 71, hostEnd: int = 99, hostStep: int = 1, routerStart: int = 254, routerEnd: int = 200, routerStep: int = -1):
        """!
        AddressAssignmentConstraint constructor.

        @param hostStart start address offset of host nodes.
        @param hostEnd end address offset of host nodes.
        @param hostStep end step of host address.
        @param routerStart start address offset of router nodes.
        @param routerEnd end address offset of router nodes.
        @param routerStep end step of router address.
        """

        self.__hostStart = hostStart
        self.__hostEnd = hostEnd
        self.__hostStep = hostStep

        self.__routerStart = routerStart
        self.__routerEnd = routerEnd
        self.__routerStep = routerStep

    def getOffsetAssigner(self, type: NodeRole) -> Assigner:
        """!
        @brief Get IP offset assigner for a type of node.

        @todo Handle pure-internal routers.

        @param type type of the node.
        @returns An int assigner that generates IP address offset.
        @throws ValueError if try to get assigner of IX interface.
        """

        if type == NodeRole.Host: return Assigner(self.__hostStart, self.__hostEnd, self.__hostStep)
        if type == NodeRole.Router: return Assigner(self.__routerStart, self.__routerEnd, self.__routerStep)

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