import dataclasses
import io
import os
import subprocess
import base64
from os.path import join as pjoin
from dataclasses import dataclass
from enum import Enum
from tempfile import TemporaryDirectory
from typing import Dict, List, NamedTuple, Optional, Tuple

from seedemu.core import (Emulator, File, Interface, Layer, Network, Node,
                          Registry, Router, ScopedRegistry)


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


class _IsolationDomain(NamedTuple):
    label: Optional[str]


@dataclass
class _AutonomousSystem:
    # def __init__(self, isd: Optional[int] = None, is_core: bool = False):
    isd: Optional[int] = None
    is_core: str = False
    cert_issuer: Optional[int] = None
    # Next IFID assigned to a link
    _next_ifid: int = dataclasses.field(default=1, kw_only=True)
    # Next UDP port assigned to a link per router
    _next_port: Dict[str, int] = dataclasses.field(default_factory=dict, kw_only=True)

    def get_next_ifid(self) -> int:
        ifid = self._next_ifid
        self._next_ifid += 1
        return ifid

    def get_next_port(self, router_name: str) -> int:
        try:
            return self._next_port[router_name]
        except KeyError:
            default_port = 50000
            self._next_port[router_name] = default_port
            return default_port


@dataclass
class _LinkEp:
    isd: int
    asn: int
    router: Router
    ifid: int
    ip: str
    port: int


class _LinkConfig(NamedTuple):
    a: _LinkEp
    b: _LinkEp
    rel: LinkType


def _format_ia(isd: int, asn: int) -> str:
    """Format a BGP-compatible SCION ASN in decimal notation"""
    assert asn < 2**32
    return f"{isd}-{asn}"


class Scion(Layer):
    """!
    @brief The SCION routing layer.

    This layer provides support for the SCION inter-domain routing architecture.
    """

    __isds: Dict[int, _IsolationDomain]
    __ases: Dict[int, _AutonomousSystem]
    __links: Dict[Tuple[int, int], LinkType]
    __ix_links: Dict[Tuple[int, int, int], LinkType]
    __link_cfg: List[_LinkConfig]

    def __init__(self):
        """!
        @brief SCION layer constructor.
        """
        super().__init__()
        self.__isds = {}
        self.__ases = {}
        self.__links = {}
        self.__ix_links = {}
        self.__link_cfg = []
        self.addDependency('Base', False, False)
        self.addDependency('Routing', False, False)

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


    def setCoreAs(self, asn: int, is_core: bool) -> 'Scion':
        """!
        @brief Set the type of an AS.

        @param asn AS whose type to set.
        @param is_core Whether the AS is of core or non-core type.
        @return self
        """
        try:
            self.__ases[asn].is_core = is_core
        except KeyError:
            self.__ases[asn] = _AutonomousSystem(is_core=is_core)
        return self

    def isCoreAs(self, asn: int) -> bool:
        """!
        @brief Check the type of an AS.

        @return Whether the AS is a core AS.
        """
        try:
            return self.__ases[asn].is_core
        except KeyError:
            return False

    def setCertIssuer(self, asn: int, issuer: int) -> 'Scion':
        """!
        @brief Set certificate issuer for a non-core AS. Ignored for core ASes.

        @param asn AS for which to set the cert issuer.
        @param issuer ASN of a SCION core as in the same ISD.
        @return self
        """
        try:
            self.__ases[asn].cert_issuer = issuer
        except KeyError:
            self.__ases[asn] = _AutonomousSystem(cert_issuer=issuer)
        return self

    def getCertIssuer(self, asn: int) -> Optional[int]:
        """!
        @brief Get the cert issuer.

        @param asn AS for which to set the cert issuer.
        @return ASN of the cert issuer or None if not set.
        """
        try:
            return self.__ases[asn].cert_issuer
        except KeyError:
            return None

    def addXcLink(self, a: int, b: int, linkType: LinkType) -> 'Scion':
        """!
        @brief Create a direct cross-connect link between to ASes.

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
        pass

    def render(self, emulator: Emulator) -> None:
        reg = emulator.getRegistry()
        self._configure_links(reg)
        with TemporaryDirectory(prefix="seed_scion") as tempdir:
            # XXX(benthor): hack to inspect temporary files after script termination
            tempdir = "/tmp/seed_scion"
            os.mkdir(tempdir)
            self._gen_scion_crypto(tempdir)
            for ((scope, type, name), obj) in reg.getAll().items():
                # Install and configure SCION on a router
                if type == 'rnode':
                    rnode: Router = obj
                    if rnode.hasAttribute("scion"):
                        self._install_scion(rnode)
                        self._provision_router(rnode, tempdir)
                # Install and configure SCION on an end host
                elif type == 'hnode':
                    hnode: Node = obj
                    self._install_scion(hnode)
                    self._provision_host(hnode, tempdir)

    def _doCreateGraphs(self, emulator: Emulator) -> None:
        # TODO: Draw a SCION topology graph
        pass

    def print(self, indent: int = 0) -> str:
        out = io.StringIO()
        # TODO: Improve output
        print("{}ScionLayer:".format(" " * indent), file=out)
        return out.getvalue()

    def _configure_links(self, reg: Registry) -> None:
        """Configure SCION links with IFIDs, IPs, ports, etc."""
        # cross-connect links
        for (a, b), rel in self.__links.items():
            a_reg = ScopedRegistry(str(a), reg)
            b_reg = ScopedRegistry(str(b), reg)

            try:
                a_router, b_router = self._get_xc_routers(a, a_reg, b, b_reg)
            except AssertionError:
                assert False, f"cannot find XC to configure link AS {a} --> AS {b}"

            a_ifaddr, _ = a_router.getCrossConnect(b, b_router.getName())
            b_ifaddr, _ = b_router.getCrossConnect(a, a_router.getName())
            a_addr = str(a_ifaddr.ip)
            b_addr = str(b_ifaddr.ip)

            self._log(f"add scion XC link: {a_addr} AS {a} -({rel})-> {b_addr} AS {b}")
            self._create_link(a, b, a_router, b_router, a_addr, b_addr, rel)

        # IX links
        for (ix, a, b), rel in self.__ix_links.items():
            ix_reg = ScopedRegistry('ix', reg)
            a_reg = ScopedRegistry(str(a), reg)
            b_reg = ScopedRegistry(str(b), reg)

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
            self._create_link(a, b, a_ixrouter, b_ixrouter, a_ixif.getAddress(), b_ixif.getAddress(), rel)

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
                     a_asn: int, b_asn: int,
                     a_router: Router, b_router: Router,
                     a_addr: str, b_addr: str,
                     rel: LinkType):
        """Create a link between SCION BRs a and b."""

        # Flag nodes that require the SCION stack
        a_router.setAttribute("scion", True)
        b_router.setAttribute("scion", True)

        a_as = self.__ases[a_asn]
        a = _LinkEp(a_as.isd, a_asn, a_router, a_as.get_next_ifid(), a_addr,
                    a_as.get_next_port(a_router.getName()))

        b_as = self.__ases[b_asn]
        b = _LinkEp(b_as.isd, b_asn, b_router, b_as.get_next_ifid(), b_addr,
                    b_as.get_next_port(b_router.getName()))

        self.__link_cfg.append(_LinkConfig(a, b, rel))

    def _gen_scion_crypto(self, tempdir: str):
        """Generate cryptographic material in a temporary directory on the host."""
        topofile = self._gen_topofile(tempdir)
        self._log("Calling scion-pki")
        try:
            result = subprocess.run(
                ["scion-pki", "testcrypto", "-t", topofile, "-o", tempdir, "--as-validity", "30d"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
        except FileNotFoundError:
            assert False, "scion-pki not found in PATH"

        self._log(result.stdout)
        assert result.returncode == 0, "scion-pki failed"

    def _gen_topofile(self, tempdir: str) -> str:
        """Generate a standard SCION .topo file representing the emulated network."""
        path = pjoin(tempdir, "seed.topo")
        with open(path, 'w') as f:
            f.write("ASes:\n")
            for asn, asys in self.__ases.items():
                f.write(f'  "{_format_ia(asys.isd, asn)}": ')
                if asys.is_core:
                    f.write("{core: true, voting: true, authoritative: true, issuing: true}\n")
                else:
                    assert asys.cert_issuer in self.__ases, f"non-core AS {asn} does not have a cert issuer"
                    assert asys.isd == self.__ases[asys.cert_issuer].isd, f"AS {asn} has cert issuer from foreign ISD"
                    f.write(f'{{cert_issuer: "{_format_ia(asys.isd, asys.cert_issuer)}"}}\n')

            f.write("links:\n")
            for a, b, rel in self.__link_cfg:
                f.write(f'  - {{a: "{_format_ia(a.isd, a.asn)}", b: "{_format_ia(b.isd, b.asn)}", ')
                f.write(f'linkAtoB: {rel.to_topo_format()}}}\n')
        return path

    def _install_scion(self, node: Node):
        """Install SCION packages on the node."""
        node.addBuildCommand(
            'echo "deb [trusted=yes] https://packages.netsec.inf.ethz.ch/debian all main"'
            ' > /etc/apt/sources.list.d/scionlab.list')
        node.addBuildCommand("apt-get update && apt-get install -y scionlab")
        node.addSoftware("apt-transport-https")
        node.addSoftware("ca-certificates")

    def _provision_router(self, rnode: Router, tempdir: str):
        # DONE: Copy crypto material from tempdir (rnode.setFile)

        #XXX(benthor): not sure if keeping filenames reflecting ISD-AS
        # data on the container is a good idea. Generating config
        # files might be easier if filenames were static and the same
        # across nodes. On the other hand, having this meta-data in
        # the file names might help with debugging
        asn = rnode.getAsn()
        isd = self.getAsIsd(asn)
        base = '/crypto'
        def myImport(name):
            rnode.importFile(pjoin(tempdir, f"AS{asn}", "crypto", name), pjoin(base, name))
        if self.__ases[asn].is_core:
            for kind in ["sensitive", "regular"]:
                myImport(pjoin("voting", f"ISD{isd}-AS{asn}.{kind}.crt"))
                myImport(pjoin("voting", f"{kind}-voting.key"))
                myImport(pjoin("voting", f"{kind}.tmpl"))
            for kind in ["root", "ca"]:
                myImport(pjoin("ca", f"ISD{isd}-AS{asn}.{kind}.crt"))
                myImport(pjoin("ca", f"cp-{kind}.key"))
                myImport(pjoin("ca", f"cp-{kind}.tmpl"))
        myImport(pjoin("as", f"ISD{isd}-AS{asn}.pem"))
        myImport(pjoin("as", "cp-as.key"))
        myImport(pjoin("as", "cp-as.tmpl"))

        #XXX(benthor): Is this filename really that stable?
        trcname = f"ISD{isd}-B1-S1.trc"
        rnode.importFile(pjoin(tempdir, f"ISD{isd}", "trcs", trcname), pjoin(base, "certs", trcname))

        # key generation stolen from scion tools/topology/cert.py
        rnode.setFile(pjoin(base, 'keys', 'master0.key'), base64.b64encode(os.urandom(16)).decode())
        rnode.setFile(pjoin(base, 'keys', 'master1.key'), base64.b64encode(os.urandom(16)).decode())

        


        # TODO: Build and install SCION config files
        # TODO: Make sure the container runs SCION on startup (rnode.appendStartCommand)

    def _provision_host(self, hnode: Node, tempdir: str):
        # TODO: Same as _provision_router but for an end host
        pass
