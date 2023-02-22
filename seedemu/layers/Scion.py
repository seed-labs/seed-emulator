from __future__ import annotations
import io
from dataclasses import dataclass
from enum import Enum
from os.path import isfile
from os.path import join as pjoin
from typing import Dict, NamedTuple, Tuple

from seedemu.core import (Emulator, Interface, Layer, Network, Registry,
                          Router, ScionAutonomousSystem, ScionRouter,
                          ScopedRegistry)
from seedemu.layers import ScionBase


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

    def __str__(self):
        return f"{self.name}"

    def to_topo_format(self) -> str:
        """Return type name as expected in .topo files."""
        if self.value == "Core":
            return "CORE"
        elif self.value == "Transit":
            return "CHILD"
        elif self.value == "Peer":
            return "PEER"
        assert False, "invalid scion link type"

    def to_json(self, a_to_b: bool) -> str:
        if self.value == "Core":
            return "CORE"
        elif self.value == "Peer":
            return "PEER"
        elif self.value == "Transit":
            if a_to_b:
                return "CHILD"
            else:
                return "PARENT"


class IA(NamedTuple):
    isd: int
    asn: int

    def __str__(self):
        return f"{self.isd}-{self.asn}"


class Scion(Layer):
    """!
    @brief This layer manages SCION inter-AS links.
    """

    __links: Dict[Tuple[IA, IA], LinkType]
    __ix_links: Dict[Tuple[int, IA, IA], LinkType]

    def __init__(self):
        """!
        @brief SCION layer constructor.
        """
        super().__init__()
        self.__links = {}
        self.__ix_links = {}
        self.addDependency('ScionIsd', False, False)

    def getName(self) -> str:
        return "Scion"

    def addXcLink(self, a: IA|Tuple[int, int], b: IA|Tuple[int, int], linkType: LinkType) -> 'Scion':
        """!
        @brief Create a direct cross-connect link between to ASes.

        @param a First AS (ISD and ASN).
        @param b Second AS (ISD and ASN).
        @param linkType Link type from a to b.

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, "Cannot link AS {} to itself.".format(a.asn)
        assert (a, b) not in self.__links, (
            "Link between AS {} and AS {} exists already.".format(a, b))

        self.__links[(a, b)] = linkType

        return self

    def addIxLink(self, ix: int, a: IA|Tuple[int, int], b: IA|Tuple[int, int], linkType: LinkType) -> 'Scion':
        """!
        @brief Create a private link between two ASes at an IX.

        @param ix IXP id.
        @param a First AS (ISD and ASN).
        @param b Second AS (ISD and ASN).
        @param linkType Link type from a to b.

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, "Cannot link AS {} to itself.".format(a)
        assert (a, b) not in self.__links, (
            "Link between AS {} and AS {} at IXP {} exists already.".format(a, b, ix))

        self.__ix_links[(ix, a, b)] = linkType

        return self

    def configure(self, emulator: Emulator) -> None:
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get('seedemu', 'layer', 'Base')
        assert issubclass(base_layer.__class__, ScionBase)

        self._configure_links(reg, base_layer)

    def render(self, emulator: Emulator) -> None:
        pass

    def _doCreateGraphs(self, emulator: Emulator) -> None:
        # TODO: Draw a SCION topology graph
        pass

    def print(self, indent: int = 0) -> str:
        out = io.StringIO()
        # TODO: Improve output
        print("{}ScionLayer:".format(" " * indent), file=out)
        return out.getvalue()

    def _configure_links(self, reg: Registry, base_layer: ScionBase) -> None:
        """Configure SCION links with IFIDs, IPs, ports, etc."""
        # cross-connect links
        for (a, b), rel in self.__links.items():
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            try:
                a_router, b_router = self._get_xc_routers(a.asn, a_reg, b.asn, b_reg)
            except AssertionError:
                assert False, f"cannot find XC to configure link AS {a} --> AS {b}"

            a_ifaddr, a_net = a_router.getCrossConnect(b.asn, b_router.getName())
            b_ifaddr, b_net = b_router.getCrossConnect(a.asn, a_router.getName())
            assert a_net == b_net
            net = reg.get('xc', 'net', a_net)
            a_addr = str(a_ifaddr.ip)
            b_addr = str(b_ifaddr.ip)

            self._log(f"add scion XC link: {a_addr} AS {a} -({rel})-> {b_addr} AS {b}")
            self._create_link(a_router, b_router, a, b, a_as, b_as,
                              a_addr, b_addr, net, rel)

        # IX links
        for (ix, a, b), rel in self.__ix_links.items():
            ix_reg = ScopedRegistry('ix', reg)
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            ix_net = ix_reg.get('net', f'ix{ix}')
            a_routers = a_reg.getByType('rnode')
            b_routers = b_reg.getByType('rnode')

            try:
                a_ixrouter, a_ixif = self._get_ix_port(a_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: AS {a} not in IX {ix}"
            try:
                b_ixrouter, b_ixif = self._get_ix_port(b_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: AS {a} not in IX {ix}"

            self._log(f"add scion IX link: {a_ixif.getAddress()} AS {a} -({rel})->"
                      f"{b_ixif.getAddress()} AS {b}")
            self._create_link(a_ixrouter, b_ixrouter, a, b, a_as, b_as,
                              str(a_ixif.getAddress()), str(b_ixif.getAddress()),
                              ix_net, rel)

    @staticmethod
    def _get_xc_routers(a: int, a_reg: ScopedRegistry, b: int, b_reg: ScopedRegistry) -> Tuple[Router, Router]:
        """Find routers responsible for a cross-connect link between a and b."""
        for router in a_reg.getByType('rnode'):
            for peer, asn in router.getCrossConnects().keys():
                if asn == b and b_reg.has('rnode', peer):
                    return (router, b_reg.get('rnode', peer))
        assert False

    @staticmethod
    def _get_ix_port(routers: ScopedRegistry, ix_net: Network) -> Tuple[Router, Interface]:
        """Find a router in 'routers' that is connected to 'ix_net' and the
        interface making the connection.
        """
        for router in routers:
            for iface in router.getInterfaces():
                if iface.getNet() == ix_net:
                    return (router, iface)
        else:
            assert False

    def _create_link(self,
                     a_router: ScionRouter, b_router: ScionRouter,
                     a_ia: IA, b_ia: IA,
                     a_as: ScionAutonomousSystem, b_as: ScionAutonomousSystem,
                     a_addr: str, b_addr: str,
                     net: Network, rel: LinkType):
        """Create a link between SCION BRs a and b."""
        a_ifid = a_as.getNextIfid()
        b_ifid = b_as.getNextIfid()
        a_port = a_router.getNextPort()
        b_port = b_router.getNextPort()

        a_iface = {
            "underlay": {
                "public": f"{a_addr}:{a_port}",
                "remote": f"{b_addr}:{b_port}",
            },
            "isd_as": str(b_ia),
            "link_to": rel.to_json(a_to_b=True),
            "mtu": net.getMtu(),
        }

        b_iface = {
            "underlay": {
                "public": f"{b_addr}:{b_port}",
                "remote": f"{a_addr}:{a_port}",
            },
            "isd_as": str(a_ia),
            "link_to": rel.to_json(a_to_b=False),
            "mtu": net.getMtu(),
        }

        # XXX(benthor): Remote interface id could probably be added
        # regardless of LinkType but might then undermine SCION's
        # discovery mechanism of remote interface ids. This way is
        # more conservative: Only add 'remote_interface_id' field to
        # dicts if LinkType is Peer.
        #
        # WARNING: As of February 2023, this feature is not yet
        # supported in upstream SCION.
        if rel == LinkType.Peer:
            a_iface["remote_interface_id"] = b_ifid
            b_iface["remote_interface_id"] = a_ifid
        
        # Create interfaces in BRs
        a_router.addScionInterface(a_ifid, a_iface)
        b_router.addScionInterface(b_ifid, b_iface)
