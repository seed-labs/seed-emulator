from typing import Dict, Tuple
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
    __dhcpStart: int
    __dhcpEnd: int
    __hostStep: int
    __routerStep: int
    __ipRanges:Dict[str, Tuple[int, int]] = {}


    def __init__(self, hostStart: int = 71, hostEnd: int = 99, hostStep: int = 1, dhcpStart: int = 101, dhcpEnd: int = 120, routerStart: int = 254, routerEnd: int = 200, routerStep: int = -1):
        """!
        AddressAssignmentConstraint constructor.

        @param hostStart start address offset of host nodes.
        @param hostEnd end address offset of host nodes.
        @param hostStep end step of host address.
        @param dhcpStart start address offset of dhcp clients.
        @param dhcpEnd end address offset of dhcp clients.
        @param routerStart start address offset of router nodes.
        @param routerEnd end address offset of router nodes.
        @param routerStep end step of router address.
        """

        self.__hostStart = hostStart
        self.__hostEnd = hostEnd
        self.__hostStep = hostStep

        self.__dhcpStart = dhcpStart
        self.__dhcpEnd = dhcpEnd

        self.__routerStart = routerStart
        self.__routerEnd = routerEnd
        self.__routerStep = routerStep

        self.__ipRanges['host'] = (hostStart, hostEnd) if hostStep > 0 else (hostEnd, hostStart)
        self.__ipRanges['dhcp'] = (dhcpStart, dhcpEnd)
        self.__ipRanges['router'] = (routerStart, routerEnd) if routerStep > 0 else (routerEnd, routerStart)
        self.__checkIpConflict()


    def setHostIpRange(self, hostStart:int , hostEnd: int, hostStep: int):
        """!
        @brief Set IP Range for host nodes

        @param hostStart start address offset of host nodes.
        @param hostEnd end address offset of host nodes.
        @param hostStep end step of host address.
        """
        self.__hostStart = hostStart
        self.__hostEnd = hostEnd
        self.__hostStep = hostStep

        self.__ipRanges['host'] = (hostStart, hostEnd) if hostStep > 0 else (hostEnd, hostStart)
        self.__checkIpConflict()
        
    def setDhcpIpRange(self, dhcpStart:int, dhcpEnd: int):
        """!
        @brief Set IP Range for DHCP Server to use
        
        @param dhcpStart start address offset of dhcp clients.
        @param dhcpEnd end address offset of dhcp clients.
        """
        self.__dhcpStart = dhcpStart
        self.__dhcpEnd = dhcpEnd
        self.__ipRanges['dhcp'] = (dhcpStart, dhcpEnd)
        self.__checkIpConflict()


    def setRouterIpRange(self, routerStart:int, routerEnd:int, routerStep: int):
        """!
        @brief Set IP Range for router nodes

        @param routerStart start address offset of router nodes.
        @param routerEnd end address offset of router nodes.
        @param routerStep end step of router address.
        """
        self.__routerStart = routerStart
        self.__routerEnd = routerEnd
        self.__routerStep = routerStep

        self.__ipRanges['router'] = (routerStart, routerEnd) if routerStep > 0 else (routerEnd, routerStart)
        self.__checkIpConflict()
        

    def __checkIpConflict(self):
        """!
        @brief Check conflict among IP Ranges
        """
        ipRangesManager = self.__ipRanges
        for type, ipRange in ipRangesManager.items():
            assert ipRange[0] < ipRange[1], "Set {}'s ip range again.".format(type)
            
        while len(ipRangesManager) > 1:
            minStartType = min(ipRangesManager.items(), key=lambda x: x[1][0])[0]
            minStartEnd = ipRangesManager.pop(minStartType)[1]
            nextMinStartType = min(ipRangesManager.items(), key=lambda x: x[1][0])[0]
            nextMinStart = ipRangesManager[nextMinStartType][0]
            assert minStartEnd < nextMinStart, "The ip ranges of {} and {} conflict".format(minStartType, nextMinStartType)

    def getDhcpIpRange(self) -> list:
        """!
        @brief Get IP range for DHCP server to use.
        """
        return [str(self.__dhcpStart), str(self.__dhcpEnd)]
        
    def getOffsetAssigner(self, type: NodeRole) -> Assigner:
        """!
        @brief Get IP offset assigner for a type of node.

        @todo Handle pure-internal routers.

        @param type type of the node.
        @returns An int assigner that generates IP address offset.
        @throws ValueError if try to get assigner of IX interface.
        """

        if NodeRole.Host == type or NodeRole.ControlService == type:
            return Assigner(self.__hostStart, self.__hostEnd, self.__hostStep)
        if NodeRole.Router == type or type == NodeRole.BorderRouter or NodeRole.OpenVpnRouter == type:
            return Assigner(self.__routerStart, self.__routerEnd, self.__routerStep)

        raise ValueError("IX IP assignment must done with mapIxAddress().")

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