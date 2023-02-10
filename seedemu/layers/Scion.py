import base64
import dataclasses
import io
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from os.path import join as pjoin
from tempfile import TemporaryDirectory
from typing import ClassVar, Dict, List, NamedTuple, Optional, Tuple, Iterable

from seedemu.core import (Emulator, File, Interface, Layer, Network, Node,
                          Registry, Router, ScopedRegistry)
from seedemu.core.enums import NodeRole


def _format_ia(isd: int, asn: int) -> str:
    """Format a BGP-compatible SCION ASN in decimal notation"""
    assert asn < 2**32
    return f"{isd}-{asn}"


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
    net: Network
    rel: LinkType

    def to_dict(self, asn: int) -> Dict:
        """Return dictionary representation from the perspective of asn"""
        assert asn == self.a.asn or asn == self.b.asn, "link not configured for given asn"

        if self.rel == LinkType.Transit:
            if asn == self.a.asn:
                link_to = "child"
                public = f"{self.a.ip}:{self.a.port}"
                remote = f"{self.b.ip}:{self.b.port}"
                ifid = str(self.a.ifid)
                remote_as = f"{self.b.isd}-{self.b.asn}"
            elif asn == self.b.asn:
                link_to = "parent"
                public = f"{self.b.ip}:{self.b.port}"
                remote = f"{self.a.ip}:{self.a.port}"
                ifid = str(self.b.ifid)
                remote_as = f"{self.a.isd}-{self.a.asn}"
        else:
            # TODO: handle peer and core link types
            pass

        return {
            "underlay": {
                "public": public,
                "remote": remote,
            },
            "isd_as": remote_as,
            "link_to": link_to,
            "mtu": self.net.getMtu(),
        }


class _IsolationDomain(NamedTuple):
    label: Optional[str]


@dataclass
class _AutonomousSystem:
    isd: Optional[int] = None
    is_core: str = False
    cert_issuer: Optional[int] = None
    # Topology dict (the AS's "topology.json")
    topology: Dict = dataclasses.field(default_factory=dict)
    # The router that runs the control service (only one CS per AS for now)
    cs_node: Optional[Router] = None
    # Next IFID assigned to a link
    _next_ifid: int = dataclasses.field(default=1)
    # Next UDP port assigned to a link per router
    _next_port: Dict[str, int] = dataclasses.field(default_factory=dict)

    _cs_name: ClassVar[str] = "cs1"

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

    def get_cs_name(self):
        return self._cs_name

    def build_topology(self, asn: int, reg: ScopedRegistry, links: Iterable[_LinkConfig]) -> None:
        """Create the AS topology definition (which can be serialized to "topology.json")

        `asn` is the AS's ASN
        `reg` should be scoped to the AS

        NOTE: This will also pick one of the AS's routers as the node to run the control service.
        """
        # General attributes
        if self.is_core:
            attributes = ["authoritative", "core", "issuing", "voting"]
        else:
            attributes = []

        # Set MTU to the smallest MTU of all AS-internal networks
        mtu = min(net.getMtu() for net in reg.getByType('net'))

        # Border routers
        border_routers = {}
        for node in reg.getByType('rnode'):
            rnode: Router = node
            interfaces = {}
            for link in links:
                if rnode == link.a.router:
                    interfaces[link.a.ifid] = link.to_dict(asn)
                elif rnode == link.b.router:
                    interfaces[link.b.ifid] = link.to_dict(asn)
            border_routers[rnode.getName()] = {
                "internal_addr": f"{rnode.getLoopbackAddress()}:30042",
                "interfaces": interfaces
            }

        # Select one of our BRs as host for the control service
        # TODO: Make sure this node will actually run the CS with the right configuration.
        self.cs_node = reg.getByType('rnode')[0]

        # Control plane
        cs_addr = f"{self.cs_node.getLoopbackAddress()}:30252"
        control_service = { self.get_cs_name(): { 'addr': cs_addr }}

        # Putting it all together
        self.topology = {
            'attributes': attributes,
            'isd_as': _format_ia(self.isd, asn),
            'mtu': mtu,
            'control_service': control_service,
            'discovery_service': control_service,
            'border_routers': border_routers,
            'colibri_service': {},
        }


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
        for asn, asys in self.__ases.items():
            asys.build_topology(asn, ScopedRegistry(str(asn), reg), self.__link_cfg)

        with TemporaryDirectory(prefix="seed_scion") as tempdir:
            # XXX(benthor): hack to inspect temporary files after script termination
            tempdir = "/tmp/seed_scion"
            os.mkdir(tempdir)
            self._gen_scion_crypto(tempdir)
            for ((scope, type, name), obj) in reg.getAll().items():
                # Install and configure SCION on a router
                #print(scope, type, name)
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

            a_ifaddr, a_net = a_router.getCrossConnect(b, b_router.getName())
            b_ifaddr, b_net = b_router.getCrossConnect(a, a_router.getName())
            assert a_net == b_net
            net = reg.get('xc', 'net', a_net)
            a_addr = str(a_ifaddr.ip)
            b_addr = str(b_ifaddr.ip)

            self._log(f"add scion XC link: {a_addr} AS {a} -({rel})-> {b_addr} AS {b}")
            self._create_link(a, b, a_router, b_router,
                              a_addr, b_addr, net, rel)

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
            self._create_link(a, b, a_ixrouter, b_ixrouter,
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
                     a_asn: int, b_asn: int,
                     a_router: Router, b_router: Router,
                     a_addr: str, b_addr: str,
                     net: Network, rel: LinkType):
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

        self.__link_cfg.append(_LinkConfig(a, b, net, rel))

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
            for a, b, _, rel in self.__link_cfg:
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
        basedir = '/etc/scion'

        # DONE: Copy crypto material from tempdir (rnode.setFile)
        self._provision_node_crypto(rnode, basedir, tempdir)

        # DONE: Build and install SCION config files
        self._provision_node_configs(rnode, basedir, tempdir)

        print(rnode)

        # TODO: Make sure the container runs SCION on startup (rnode.appendStartCommand)

    def _provision_host(self, hnode: Node, tempdir: str):
        # TODO: Same as _provision_router but for an end host
        pass

    def _provision_node_crypto(self, node: Node, basedir: str, tempdir: str):
        asn = node.getAsn()
        isd = self.getAsIsd(asn)
        base = basedir
        def myImport(name):
            node.importFile(pjoin(tempdir, f"AS{asn}", "crypto", name), pjoin(base, "crypto", name))
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

        #XXX(benthor): respect certificate issuer here?
        trcname = f"ISD{isd}-B1-S1.trc"
        node.importFile(pjoin(tempdir, f"ISD{isd}", "trcs", trcname), pjoin(base, "certs", trcname))

        # key generation stolen from scion tools/topology/cert.py
        node.setFile(pjoin(base, 'keys', 'master0.key'), base64.b64encode(os.urandom(16)).decode())
        node.setFile(pjoin(base, 'keys', 'master1.key'), base64.b64encode(os.urandom(16)).decode())

    def _provision_node_configs(self, node: Node, basedir: str, tempdir: str):
        asn = node.getAsn()
        isd = self.getAsIsd(asn)
        asys = self.__ases[asn]

        general = lambda name: f'[general]\nid = "{name}"\nconfig_dir = "{basedir}"\n\n[log.console]\nlevel = "info"\n\n'
        trust = lambda name: f'[trust_db]\nconnection = "/cache/{name}.trust.db"\n\n'
        path  = lambda name: f'[path_db]\nconnection = "/cache/{name}.path.db"\n\n'

        # AS Topology
        node.setFile(pjoin(basedir, 'topology.json'), json.dumps(asys.topology, indent=2))

        # Border router
        br = node.getName()
        node.setFile(pjoin(basedir, br + ".toml"), general(br))

        # Control service
        if node == asys.cs_node:
            cs_name = asys.get_cs_name()

            beacon = f'[beacon_db]\nconnection = "/cache/{cs_name}.beacon.db"\n\n'
            node.setFile(
                pjoin(basedir, 'cs1.toml'),
                f'{general(cs_name)}{trust(cs_name)}{beacon}{path(cs_name)}[ca]\nmode = "in-process"',
            )

        # Sciond
        sd = "sd1"
        node.setFile(
            pjoin(basedir, 'sd.toml'),
            f'{general(sd)}{trust(sd)}{path(sd)}',
        )

        # Dispatcher
        node.setFile(pjoin(basedir, 'disp.toml'), '[dispatcher]\nid = "dispatcher"\n')
