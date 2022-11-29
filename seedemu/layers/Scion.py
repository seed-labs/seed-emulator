import io
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Tuple

from seedemu.core import Emulator, Layer


class LinkType(Enum):
    """!
    @brief Type of a SCION link between two ASes.
    """

    ## Core link between core ASes.
    Core = "Core"

    ## Customer-Provider transit link.
    Transit = "Transit"

    ## Non-core AS peering link.
    Peer = "Peer"


class _IsolationDomain(NamedTuple):
    label: Optional[str]


class _AutonomousSystem:
    def __init__(self, isd: Optional[int] = None, isCore: bool = False):
        self.isd = isd
        self.isCore = isCore


class Scion(Layer):
    """!
    @brief The SCION routing layer.

    This layer provides support for the SCION inter-domain routing architecture
    in all routers and hosts.
    """

    __isds: Dict[int, _IsolationDomain]
    __ases: Dict[int, _AutonomousSystem]
    __links: Dict[Tuple[int, int], LinkType]
    __ix_links : Dict[Tuple[int, int, int], LinkType]

    def __init__(self):
        """!
        @brief SCION layer constructor.
        """
        super().__init__()
        self.__isds = {}
        self.__ases = {}
        self.__links = {}
        self.__ix_links = {}
        self.addDependency('Base', False, False)

    def getName(self) -> str:
        return "Scion"

    def addIsd(self, isd: int, label: Optional[str] = None) -> 'Scion':
        """!
        @brief Add an insolation domain.

        @param isd ISD ID.
        @param label Descriptive name for the ISD.
        @throws AssertionError if ISD already exists.

        @returns self
        """
        assert isd not in self.__isds
        self.__isds[isd] = _IsolationDomain(label)

        return self

    def getIsds(self) -> List[Tuple[int, str]]:
        """!
        @brief Get a list of all ISDs.

        @returns List of ISD ID and label tuples.
        """
        return [(id, isd.label) for id, isd in self.__isds.items()]

    def setAsIsd(self, asn: int, isd: int) -> 'Scion':
        """!
        @brief Set which ISD an AS belongs to.

        An AS can only belong to a single ISD at a time. If another ISD was
        previously assigned, it is overwritten with the new assignment.

        @param asn ASN to assign an ISD to.
        @param isd The ISD ID to assign.

        @returns self
        """
        try:
            self.__ases[asn].isd = isd
        except KeyError:
            self.__ases[asn] = _AutonomousSystem(isd, False)
        return self

    def getAsIsd(self, asn: int) -> Optional[Tuple[int, str]]:
        """!
        @brief Get the ISD an AS belongs to.

        @returns Tuple of the assigned ISD ID and ISD label or None if no ISD
        has been assigned yet.
        """
        try:
            return self.__ases[asn].isd
        except KeyError:
            return None


    def setCoreAs(self, asn: int, isCore: bool) -> 'Scion':
        """!
        @brief Set the type of an AS.

        @param asn AS whose type to set.
        @param isCore Whether the AS is of core or non-core type.
        @return self
        """
        try:
            self.__ases[asn].isCore = isCore
        except KeyError:
            self.__ases[asn] = _AutonomousSystem(isCore=isCore)
        return self

    def isCoreAs(self, asn: int) -> bool:
        """!
        @brief Check the type of an AS.

        @return Whether the AS is a core AS.
        """
        try:
            return self.__ases[asn].isCore
        except KeyError:
            return False

    def addLink(self, a: int, b: int, linkType: LinkType) -> 'Scion':
        """!
        @brief Create a direct link between to ASes.

        @param a First ASN.
        @param b Second ASN.
        @param linkType Link type from a to b.

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        assert a != b, "Cannot link AS {} to itself.".format(a)
        assert (a, b) not in self.__links, (
            "Link between AS {} and AS {} exists already.".format(a, b))

        self.__links[(a, b)] = linkType

        return self

    def addIxLink(self, ix: int, a: int, b: int, linkType: LinkType) -> 'Scion':
        """!
        @brief Create a private link between two ASes at an IX.

        @param ix IXP id.
        @param a First ASN.
        @param b Second ASN.
        @param linkType Link type from a to b.

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        assert a != b, "Cannot link AS {} to itself.".format(a)
        assert (a, b) not in self.__links, (
            "Link between AS {} and AS {} at IXP {} exists already.".format(a, b, ix))

        self.__ix_links[(ix, a, b)] = linkType

        return self

    def configure(self, emulator: Emulator) -> None:
        self._log("Configuring Scion layer")

        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rnode':
                # Install and configure SCION on a router
                pass
            elif type == 'hnode':
                # Install and configure SCION on an end host
                pass


    def render(self, emulator: Emulator) -> None:
        self._log("Rendering Scion layer")

        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rnode':
                # Install and configure SCION on a router
                pass
            elif type == 'hnode':
                # Install and configure SCION on an end host
                pass

    def _doCreateGraphs(self, emulator: Emulator) -> None:
        pass

    def print(self, indent: int = 0) -> str:
        out = io.StringIO()
        print("{}ScionLayer:".format(" " * indent), file=out)
        return out.getvalue()
