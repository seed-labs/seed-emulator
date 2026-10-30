from __future__ import annotations
from .Base import Base
from .Ospf import Ospf
from .Ibgp import Ibgp
from seedemu.core import Node, ScopedRegistry, Graphable, Emulator, Layer, Router
from seedemu.core.enums import NetworkType, NodeRole
from typing import List, Tuple, Set
from ._bgp_metadata import (
    BGP_BACKEND_FRR,
    get_bgp_backend,
    install_router_bgp_session,
    set_mpls_ldp_intent,
)

MPLS_PRESERVED_IBGP_MODES = {"route-reflector"}
MPLS_DISABLED_IBGP_MODES = {"disabled"}
MPLS_CORE_FORWARDING = "mpls"
MPLS_EDGE_BGP_SCOPE = "edge-only"

class Mpls(Layer, Graphable):
    """!
    @brief The Mpls (MPLS) layer.

    This layer is a replacement for the iBGP full mesh setup for the transit
    provider's internal network. Instead of the traditional IP network, which
    requires every hop to have a copy of the full table, MPLS allows non-edge
    hops to hold only the MPLS forwarding table, which negated the need for the
    full table.

    MPLS layer will setup iBGP, LDP, and OSPF. This path requires routers in
    MPLS-enabled ASes to use the FRR routing backend because BIRD does not
    provide the MPLS/LDP support used here. When installed, the MPLS layer will
    treat all nodes with (1) no connection to IX and (2) no connection to a
    network with at least one host node as non-edge nodes and will not put it
    as part of the iBGP mesh network.
    
    The MPLS layer requires kernel modules support. Make sure you load the
    following modules:

    - mpls_router
    - mpls_iptunnel
    - mpls_gso

    Node with MPLS enabled will be privileged. This means the container
    potentially have full control over the docker host. Be careful when exposing
    the node to the public.
    """

    __additional_edges: Set[Tuple[int, str]]
    __enabled: Set[int]

    def __init__(self):
        """!
        @brief Mpls layer constructor.
        """
        super().__init__()
        self.__additional_edges = set()
        self.__enabled = set()

        # they are not really "dependency," we just need them to render after
        # us, in case we need to setup masks.
        self.addDependency('Ospf', True, True)
        self.addDependency('Ibgp', True, True)

        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return 'Mpls'

    def markAsEdge(self, asn: int, nodename: str) -> Mpls:
        """!
        @brief Mark a router node as edge node.

        By default, only nodes with connection to IX, or connection to a network
        with at least one host node, will be considered an edge router and be
        included in the iBGP mesh. Use this method to mark a node as edge
        manually.

        @param asn asn
        @param nodename name of node

        @returns self, for chaining API calls.
        """
        self.__additional_edges.add((asn, nodename))

        return self

    def getEdges(self) -> Set[Tuple[int, str]]:
        """!
        @brief Get set of router nodes marked as edge.

        @returns set of tuple of asn and node name.
        """
        return self.__additional_edges

    def enableOn(self, asn: int) -> Mpls:
        """!
        @brief Use MPLS in an AS.

        MPLS is not enabled by default. Use this method to enable MPLS for an
        AS. This also automatically setup masks for OSPF and IBGP layer if they
        exist.

        @param asn ASN.

        @returns self, for chaining API calls.
        """
        self.__enabled.add(asn)

        return self

    def getEnabled(self) -> Set[int]:
        """!
        @brief Get set of ASNs that has MPLS enabled.

        @return set of ASNs
        """
        return self.__enabled

    def __syncAsLevelEnabled(self, emulator: Emulator) -> Set[int]:
        reg = emulator.getRegistry()
        if reg.has('seedemu', 'layer', 'Base'):
            base: Base = reg.get('seedemu', 'layer', 'Base')
            for asn in base.getAsns():
                asobj = base.getAutonomousSystem(asn)
                if hasattr(asobj, "getCoreForwarding") and asobj.getCoreForwarding() == MPLS_CORE_FORWARDING:
                    self.__enabled.add(asn)
        return set(self.__enabled)

    def __getAsObject(self, emulator: Emulator, asn: int):
        reg = emulator.getRegistry()
        if reg.has('seedemu', 'layer', 'Base'):
            base: Base = reg.get('seedemu', 'layer', 'Base')
            return base.getAutonomousSystem(asn)
        return None

    def __getExplicitIbgpMode(self, emulator: Emulator, asn: int):
        asobj = self.__getAsObject(emulator, asn)
        if asobj is not None:
            if hasattr(asobj, "hasIbgpMode") and asobj.hasIbgpMode():
                return asobj.getIbgpMode()
        reg = emulator.getRegistry()
        if reg.has('seedemu', 'layer', 'Ibgp'):
            ibgp: Ibgp = reg.get('seedemu', 'layer', 'Ibgp')
            if asn in ibgp.getMaskedAsns():
                return "disabled"
        return None

    def __preserveExistingIbgp(self, emulator: Emulator, asn: int) -> bool:
        asobj = self.__getAsObject(emulator, asn)
        if asobj is not None:
            if asobj.getIbgpMode() in MPLS_PRESERVED_IBGP_MODES:
                return True
            if asobj.getIbgpMode() == "full-mesh" and asobj.getBgpScope() == MPLS_EDGE_BGP_SCOPE:
                return True
        return self.__getExplicitIbgpMode(emulator, asn) in MPLS_PRESERVED_IBGP_MODES

    def __installMplsIbgp(self, emulator: Emulator, asn: int) -> bool:
        mode = self.__getExplicitIbgpMode(emulator, asn)
        return mode not in MPLS_PRESERVED_IBGP_MODES and mode not in MPLS_DISABLED_IBGP_MODES

    def __maskExistingControlPlaneLayers(self, emulator: Emulator) -> None:
        """Mask OSPF/iBGP before those layers record non-MPLS intent."""
        reg = emulator.getRegistry()
        for asn in self.__syncAsLevelEnabled(emulator):
            if reg.has('seedemu', 'layer', 'Ospf'):
                self._log('Ospf layer exists, masking as{}'.format(asn))
                ospf: Ospf = reg.get('seedemu', 'layer', 'Ospf')
                ospf.maskAsn(asn)

            if reg.has('seedemu', 'layer', 'Ibgp') and not self.__preserveExistingIbgp(emulator, asn):
                self._log('Ibgp layer exists, masking as{}'.format(asn))
                ibgp: Ibgp = reg.get('seedemu', 'layer', 'Ibgp')
                ibgp.maskAsn(asn)

    def __getEdgeNodes(self, scope: ScopedRegistry) -> Tuple[List[Node], List[Node]]:
        """!
        @brief Helper tool - get list of routers (edge, non-edge) of an AS.

        @param scope scope.
        """
        enodes: List[Node] = []
        nodes: List[Node] = []

        for obj in scope.getByType('rnode'):
            node: Node = obj

            is_edge = False
            for iface in node.getInterfaces():
                net = iface.getNet()
                if net.getType() == NetworkType.InternetExchange:
                    is_edge = True
                    break
                if True in (node.getRole() == NodeRole.Host for node in net.getAssociations()):
                    is_edge = True
                    break

            if is_edge: enodes.append(node)
            else: nodes.append(node)

        return (enodes, nodes)

    def __addAdditionalEdges(self, scope: ScopedRegistry, asn: int, enodes: List[Node]) -> List[Node]:
        names = {node.getName() for node in enodes}
        for (asn_, nodename) in self.__additional_edges:
            if asn_ != asn:
                continue
            if scope.has('rnode', nodename) and nodename not in names:
                node = scope.get('rnode', nodename)
                enodes.append(node)
                names.add(nodename)
        return enodes

    def __recordLdpOspfIntent(self, node: Router):
        """!
        @brief Record LDP and OSPF intent on router.

        @param node node.
        """
        backend = get_bgp_backend(node)
        assert backend == BGP_BACKEND_FRR, (
            "MPLS requires FRR routing backend; AS{}/{} uses {}. "
            "BIRD does not support MPLS/LDP in this emulator path."
        ).format(node.getAsn(), node.getName(), backend)

        self._log('Recording LDP and OSPF intent on as{}/{}'.format(node.getAsn(), node.getName()))

        node.setPrivileged(True)
        node.addSoftware('frr')

        mpls_iface_list = []

        for iface in node.getInterfaces():
            net = iface.getNet()
            if net.getType() == NetworkType.InternetExchange: continue
            if not (True in (node.getRole() == NodeRole.Router or node.getRole() == NodeRole.OpenVpnRouter for node in net.getAssociations())): continue
            mpls_iface_list.append(net.getName())
            net.setMtu(9000)

        set_mpls_ldp_intent(node, mpls_iface_list)

    def __setUpIbgpMesh(self, nodes: List[Router]):
        """!
        @brief Setup IBGP full mesh.

        @param node list of nodes.
        """

        self._log('Setting up iBGP full mesh for edge nodes...')
        for local in nodes:

            n = 1
            for remote in nodes:
                if local == remote: continue

                install_router_bgp_session(
                    local,
                    {
                        "name": "mpls_ibgp{}".format(n),
                        "kind": "ibgp",
                        "local_address": str(local.getLoopbackAddress()),
                        "local_asn": local.getAsn(),
                        "peer_address": str(remote.getLoopbackAddress()),
                        "peer_asn": local.getAsn(),
                        "export_policy": "all",
                        "next_hop_self": False,
                        "igp_table": "master4",
                    },
                )

                n += 1

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        enabled = self.__syncAsLevelEnabled(emulator)
        install_mpls_ibgp = {
            asn: self.__installMplsIbgp(emulator, asn)
            for asn in enabled
        }
        self.__maskExistingControlPlaneLayers(emulator)
        reg = emulator.getRegistry()
        for asn in enabled:
            scope = ScopedRegistry(str(asn), reg)
            (enodes, nodes) = self.__getEdgeNodes(scope)
            enodes = self.__addAdditionalEdges(scope, asn, enodes)
            if install_mpls_ibgp[asn]:
                self.__setUpIbgpMesh(enodes)
            for n in enodes: self.__recordLdpOspfIntent(n)
            for n in nodes: self.__recordLdpOspfIntent(n)

    def render(self, emulator: Emulator):
        pass

    def _doCreateGraphs(self, emulator: Emulator):
        base = emulator.getRegistry().get('seedemu', 'layer', 'Base')
        enabled = self.__syncAsLevelEnabled(emulator)
        for asn in base.getAsns():
            if asn not in enabled: continue
            asobj = base.getAutonomousSystem(asn)
            asobj.createGraphs(emulator)
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            mplsgraph = self._addGraph('AS{}: MPLS Topology'.format(asn), False)
            mplsgraph.copy(l2graph)
            for edge in mplsgraph.edges:
                edge.style = 'dotted'

            scope = ScopedRegistry(str(asn), emulator.getRegistry())
            (enodes, _) = self.__getEdgeNodes(scope)
            
            while len(enodes) > 0:
                a = enodes.pop()
                for b in enodes:
                    mplsgraph.addEdge('Router: {}'.format(a.getName()), 'Router: {}'.format(b.getName()), style = 'solid')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'MplsLayer:\n'
        
        indent += 4
        out += ' ' * indent
        out += 'Enabled on:\n'

        indent += 4
        for asn in self.__enabled:
            out += ' ' * indent
            out += 'as{}\n'.format(asn)

        return out
