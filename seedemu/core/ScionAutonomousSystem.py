from __future__ import annotations
import base64
import os
from collections import defaultdict
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

from .AutonomousSystem import AutonomousSystem
from .Emulator import Emulator
from .enums import NodeRole
from .Node import Node, ScionRouter

class ScionASN:
    """!
    @brief: ASN identifier for a SCION AS.
    """
    asn: int
    BGP_ASN_BITS = 32
    MAX_BGP_ASN = (1 << BGP_ASN_BITS) - 1
    GROUP_BITS = 16
    GROUP_MAX_VALUE = (1 << GROUP_BITS) - 1

    def __init__(self, asn):
        """!
        @brief Constructor for SCION AS

        @param asn The SCION ASN that should be handled.
        """
        self.asn = asn

    def getAsn(self) -> int:
        """!
        @brief Return ASN as integer.

        @returns ASN as integer
        """
        return self.asn

    def __split(self):
        """!
        @brief Splits ASN into 16 bit groups.

        @returns 3-tuple of ASN grouped into 16 bit blocks
        """
        return (self.asn >> 2 * self.GROUP_BITS) & self.GROUP_MAX_VALUE, \
               (self.asn >> self.GROUP_BITS) & self.GROUP_MAX_VALUE, \
               (self.asn) & self.GROUP_MAX_VALUE

    def getFileStr(self) -> str:
        """!
        @brief Return ASN as snake case string for file access.

        @returns ASN as string
        """
        if self.asn <= self.MAX_BGP_ASN:
            # BGP style ASN
            return str(self.asn)
        else:
            # SCION style hexadecimal ASN in three groups
            return "%x_%x_%x" % (self.__split())

    def __str__(self) -> str:
        """!
        @brief Return ASN string in colon-hex-format.

        @returns ASN as string.
        """
        if self.asn <= self.MAX_BGP_ASN:
            # BGP style ASN
            return str(self.asn)
        else:
            # SCION style hexadecimal ASN in three groups
            return "%x:%x:%x" % (self.__split())


class IA:
    """!
    @brief ISD-ASN identifier for a SCION AS.
    """
    isd: int
    asn: int
    asn_object: ScionASN

    def __init__(self, isd: int, asn):
        """!
        @brief Return ASN as integer.

        @param isd ISD part of the identifier
        @param asn ASN part of the identifier as integer or ScionASN object
        """
        self.isd = isd
        if type(asn) is int:
            self.asn = asn
            self.asn_object = ScionASN(asn)
        elif type(asn) is ScionASN:
            self.asn_object = asn
            self.asn = self.asn_object.getAsn()

    def __str__(self) -> str:
        """!
        @brief Return ASN as string in colon-hex-format.

        @returns ASN as string.
        """
        return f"{self.isd}-{self.asn_object}"

    def __hash__(self) -> int:
        """!
        @brief Allows using IA as key for dicts etc.

        @returns hash value.
        """
        return (self.isd, self.asn).__hash__()

    def __eq__(self, other) -> bool:
        """!
        @brief Enable comparison of IA with tupels and other IA instances.

        @returns True or False, depending on the equality of ISD and ASN.
        """
        if isinstance(other, Tuple):
            return (self.isd == other[0]) and (self.asn == other[1])
        elif isinstance(other, IA):
            return (self.isd == other.isd) and (self.asn == other.asn)
        return False


class ScionAutonomousSystem(AutonomousSystem):
    """!
    @brief SCION-enabled AutonomousSystem.

    This class represents an autonomous system with support for SCION.
    """

    __scion_asn: ScionASN
    __keys: Optional[Tuple[str, str]]
    __attributes: Dict[int, Set]         # Set of AS attributes per ISD
    __mtu: Optional[int]                 # Minimum MTU in the AS's internal networks
    __control_services: Dict[str, Node]
    # Origination, propagation, and registration intervals
    __beaconing_intervals: Tuple[Optional[str], Optional[str], Optional[str]]
    __beaconing_policy: Dict[str, Dict]
    __note: str # optional free form parameter that contains interesting information about AS. This will be included in beacons if it is set
    __generateStaticInfoConfig:  bool

    def __init__(self, asn: int, subnetTemplate: str = "10.{}.0.0/16"):
        """!
        @copydoc AutonomousSystem
        """
        super().__init__(asn, subnetTemplate)
        self.__scion_asn = ScionASN(asn)
        self.__control_services = {}
        self.__keys = None
        self.__attributes = defaultdict(set)
        self.__mtu = None
        self.__beaconing_intervals = (None, None, None)
        self.__beaconing_policy = {}
        self.__note = None
        self.__generateStaticInfoConfig = False
    

    def registerNodes(self, emulator: Emulator):
        """!
        @copydoc AutonomousSystem.registerNodes()
        """
        super().registerNodes(emulator)
        reg = emulator.getRegistry()
        asn = str(self.getAsn())
        for (key, val) in self.__control_services.items(): reg.register(asn, 'csnode', key, val)

    def configure(self, emulator: Emulator):
        """!
        @copydoc AutonomousSystem.configure()
        """
        super().configure(emulator)

        for cs in self.__control_services.values():
            if len(cs.getNameServers()) == 0:
                cs.setNameServers(self.getNameServers())
            cs.configure(emulator)

        # Set MTU to the smallest MTU of all AS-internal networks
        reg = emulator.getRegistry()
        self.__mtu = min(net.getMtu() for net in reg.getByType(str(self.getAsn()), 'net'))

        # Create secret keys
        self.__keys = (
            base64.b64encode(os.urandom(16)).decode(),
            base64.b64encode(os.urandom(16)).decode())


    def getSecretKeys(self) -> Tuple[str, str]:
        """!
        @brief Get AS secret keys.
        """
        assert self.__keys is not None, "AS is not configured yet"
        return self.__keys

    def setAsAttributes(self, isd: int, attributes: Iterable[str]) -> ScionAutonomousSystem:
        """!
        @brief Set an AS's attributes. Called during configuration.

        @param isd To which ISD the attributes apply.
        @param attributes List of attributes. Replaces any attributes previously configured.
        @returns self
        """
        self.__attributes[isd] = set(attributes)
        return self

    def getAsAttributes(self, isd: int) -> List[str]:
        """!
        @brief Get all AS attributes.

        @param isd To which ISD the attributes apply.
        @returns List of attributes.
        """
        return list(self.__attributes[isd])

    def setBeaconingIntervals(self,
        origination: Optional[str] = None,
        propagation: Optional[str] = None,
        registration: Optional[str] = None
        ) -> ScionAutonomousSystem:
        """!
        @brief Set the beaconing intervals. Intervals are specified as string of a positive decimal
        integer followed by one of the units y, w, d, h, m, s, us, or ns. Setting an interval to
        None uses the beacon server's default setting.

        @returns self
        """
        self.__beaconing_intervals = (origination, propagation, registration)
        return self

    def getBeaconingIntervals(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """!
        @brief Get the beaconing intervals.

        @returns Tuple of origination, propagation, and registration interval.
        """
        return self.__beaconing_intervals

    def setBeaconPolicy(self, type: str, policy: Optional[Dict]) -> ScionAutonomousSystem:
        """!
        @brief Set the beaconing policy of the AS.

        @param type One of "propagation", "core_registration", "up_registration", "down_registration".
        @param policy Policy. Setting a policy to None clears it.
        @returns self
        """
        types = ["propagation", "core_registration", "up_registration", "down_registration"]
        assert type in types, "Unknown policy type"
        self.__beaconing_policy[type] = policy
        return self

    def getBeaconingPolicy(self, type: set) -> Optional[Dict]:
        """!
        @brief Get the beaconing policy of the AS.

        @param type One of "propagation", "core_registration", "up_registration", "down_registration".
        @returns Policy or None if no policy of the requested type is set.
        """
        types = ["propagation", "core_registration", "up_registration", "down_registration"]
        assert type in types, "Unknown policy type"
        return self.__beaconing_policy.get(type)

    def getTopology(self, isd: int) -> Dict:
        """!
        @brief Create the AS topology definition.

        Called during rendering.

        @param isd ISD for which to generate the AS topology.
        @return Topology dictionary (can be serialized to "topology.json")
        """
        # Control service
        control_services = {}
        for name, cs in self.__control_services.items():
            ifaces = cs.getInterfaces()
            if len(ifaces) > 0:
                cs_addr = f"{ifaces[0].getAddress()}:30254"
                control_services[name] = { 'addr': cs_addr }

        # Border routers
        border_routers = {}
        for router in self.getBorderRouters():
            rnode: ScionRouter = self.getRouter( router.getName() )

            localIP = rnode.getLocalIPAddress()
            listen_addr = localIP if localIP else rnode.getLoopbackAddress()
            #UDP address on which the router receives SCION packets 
            # from sibling routers and end hosts in this AS.
            border_routers[rnode.getName()] = {
                "internal_addr": f"{listen_addr}:30042",
                "interfaces": rnode.getScionInterfaces()
            }

        return {
            'attributes': self.getAsAttributes(isd),
            'isd_as': f'{IA(isd, self.getScionAsn())}',
            'mtu': self.__mtu,
            'control_service': control_services,
            'discovery_service': control_services,
            'border_routers': border_routers,
            'dispatched_ports': '31000-32767',
        }

    def createControlService(self, name: str) -> Node:
        """!
        @brief Create a SCION control service node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__control_services, 'Control service with name {} already exists.'.format(name)
        self.__control_services[name] = Node(name, NodeRole.ControlService, self.getAsn())

        return self.__control_services[name]

    def getControlServices(self) -> List[str]:
        """!
        @brief Get list of names of SCION control services.

        @returns list of routers.
        """
        return list(self.__control_services.keys())

    def getControlService(self, name: str) -> Node:
        """!
        @brief Retrieve a control service node.

        @param name name of the node.
        @returns Node.
        """
        return self.__control_services[name]

    def setNote(self, note: str) -> ScionAutonomousSystem:
        """!
        @brief Set a note for the AS.

        @param note Note.
        @returns self
        """
        self.__note = note
        return self 

    def getNote(self) -> Optional[str]:
        """!
        @brief Get the note for the AS.

        @returns Note or None if no note is set.
        """
        return self.__note

    def setGenerateStaticInfoConfig(self, generateStaticInfoConfig: bool) -> ScionAutonomousSystem:
        """!
        @brief Set the generateStaticInfoConfig flag.

        @param generateStaticInfoConfig Flag.
        @returns self
        """
        self.__generateStaticInfoConfig = generateStaticInfoConfig
        return self

    def getGenerateStaticInfoConfig(self) -> bool:
        """!
        @brief Get the generateStaticInfoConfig flag.

        @returns Flag.
        """
        return self.__generateStaticInfoConfig

    def getScionAsn(self):
        return self.__scion_asn

    def _doCreateGraphs(self, emulator: Emulator):
        """!
        @copydoc AutonomousSystem._doCreateGraphs()
        """
        super()._doCreateGraphs(emulator)
        asn = self.getScionAsn()
        l2graph = self.getGraph('AS{}: Layer 2 Connections'.format(asn.getAsn()))
        for obj in self.__control_services.values():
            router: Node = obj
            rtrname = 'CS: {}'.format(router.getName(), group = 'AS{}'.format(asn.getAsn()))
            l2graph.addVertex(rtrname, group = 'AS{}'.format(asn))
            for iface in router.getInterfaces():
                net = iface.getNet()
                netname = 'Network: {}'.format(net.getName())
                l2graph.addEdge(rtrname, netname)

    def print(self, indent: int) -> str:
        """!
        @copydoc AutonomousSystem.print()
        """
        out = super().print(indent)

        out += ' ' * indent
        out += 'SCION Control Services:\n'

        for node in self.__control_services.values():
            out += node.print(indent + 4)

        return out
