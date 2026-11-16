from __future__ import annotations
from seedemu.core.enums import NetworkType, NodeRole
from .Base import Base
from seedemu.core import ScopedRegistry, Node, Graphable, Emulator, Layer
from typing import Dict, List, Optional, Set, Tuple
from ._bgp_metadata import (
    DEFAULT_BGP_HOLD_TIME,
    DEFAULT_BGP_KEEPALIVE_TIME,
    install_router_bgp_session,
    normalize_bgp_timers,
)

IBGP_MODE_FULL_MESH = "full-mesh"
IBGP_MODE_ROUTE_REFLECTOR = "route-reflector"
IBGP_MODE_DISABLED = "disabled"

IBGP_MODES = {
    IBGP_MODE_FULL_MESH,
    IBGP_MODE_ROUTE_REFLECTOR,
    IBGP_MODE_DISABLED,
}


class Ibgp(Layer, Graphable):
    """!
    @brief The Ibgp (iBGP) layer.

    This layer automatically sets up full-mesh iBGP or Route Reflector based
    iBGP sessions between routers within each AS.
    """
    __masked: Set[int]
    __hold_time: int
    __keepalive_time: int

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        super().__init__()
        self.__masked = set()
        self.__hold_time = DEFAULT_BGP_HOLD_TIME
        self.__keepalive_time = DEFAULT_BGP_KEEPALIVE_TIME
        self.addDependency('Ospf', False, False)

    def __dfs(self, start: Node, visited: List[Node], netname: str = 'self'):
        """!
        @brief do a DFS and find all local routers to setup IBGP.

        @param start node to start from.
        @param visited list to store nodes.
        @param netname name of the net - for log only.
        """
        if start in visited:
            return
        
        self._log('found node: as{}/{} via {}'.format(start.getAsn(), start.getName(), netname))
        visited.append(start)

        for iface in start.getInterfaces():
            net = iface.getNet()

            if net.getType() != NetworkType.Local:
                continue

            neighs: List[Node] = net.getAssociations()

            for neigh in neighs:
                role = neigh.getRole()
                if role != NodeRole.Router and role != NodeRole.BorderRouter and role != NodeRole.OpenVpnRouter: 
                    continue
                
                self.__dfs(neigh, visited, net.getName())


    def getName(self) -> str:
        return 'Ibgp'

    def setTimers(
        self,
        holdTime: Optional[int] = None,
        keepaliveTime: Optional[int] = None,
    ) -> Ibgp:
        """!
        @brief Set default iBGP hold and keepalive timers.

        @param holdTime BGP hold time, in seconds.
        @param keepaliveTime BGP keepalive time, in seconds.

        @returns self, for chaining API calls.
        """
        timers = normalize_bgp_timers(
            self.__hold_time if holdTime is None else holdTime,
            self.__keepalive_time if keepaliveTime is None else keepaliveTime,
        )
        self.__hold_time = timers["hold_time"]
        self.__keepalive_time = timers["keepalive_time"]
        return self

    def getTimers(self) -> Dict[str, int]:
        """!
        @brief Get iBGP timer defaults used by this layer.

        @returns dict with hold_time and keepalive_time.
        """
        return {
            "hold_time": self.__hold_time,
            "keepalive_time": self.__keepalive_time,
        }

    def maskAsn(self, asn: int) -> Ibgp:
        """!
        @brief Mask an AS.

        By default, Ibgp layer will add iBGP peering for all ASes. Use this
        method to mask an AS and disable iBGP.

        @param asn AS to mask.

        @returns self, for chaining API calls.
        """
        self.__masked.add(asn)

        return self
    
    def getMaskedAsns(self) -> Set[int]:
        """!
        @brief Get set of masked ASNs.
        
        @return set of ASNs.
        """
        return self.__masked

    def __is_ibgp_disabled(self, router: Node) -> bool:
        return hasattr(router, "isControlPlaneDisabled") and router.isControlPlaneDisabled("ibgp")

    def __get_igp_table(self, emulator: Emulator, asn: int) -> str:
        reg = emulator.getRegistry()
        if reg.has('seedemu', 'layer', 'Mpls'):
            mpls = reg.get('seedemu', 'layer', 'Mpls')
            if hasattr(mpls, "getEnabled") and asn in mpls.getEnabled():
                return "master4"
        return "t_ospf"

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()
        base: Base = reg.get('seedemu', 'layer', 'Base')
        for asn in base.getAsns():
            asobj = base.getAutonomousSystem(asn)
            if int(asn) in self.__masked:
                asobj.setIbgpMode(IBGP_MODE_DISABLED)

            asobj.completeIbgpSetup()
            mode = asobj.getIbgpMode()
            if mode == IBGP_MODE_DISABLED: continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn), reg).getByType('rnode')
            routers_map: Dict[str, Node] = {router.getName(): router for router in routers}
            participant_names = asobj.getIbgpParticipants()
            disabled = {name for name, router in routers_map.items() if self.__is_ibgp_disabled(router)}
            active_names = participant_names - disabled
            active_routers_map = {
                name: router for name, router in routers_map.items()
                if name in active_names
            }
            igp_table = self.__get_igp_table(emulator, asn)

            if mode == IBGP_MODE_ROUTE_REFLECTOR:
                clusters = asobj._aggregateBgpClusters()
                self._render_rr_mode(asn, clusters, active_routers_map, igp_table)
                continue

            self._render_full_mesh_mode(
                asn,
                [active_routers_map[name] for name in sorted(active_routers_map.keys())],
                igp_table,
            )

    def _render_rr_mode(self, asn: int, clusters: Dict[str, Tuple[Set[str], Set[str]]], routers_map: Dict[str, Node], igp_table: str = "t_ospf"):
        """!
        @brief Render Route Reflector based iBGP sessions for one AS.

        @param asn AS number being rendered.
        @param clusters mapping from cluster ID to RR names and client names.
        @param routers_map mapping from router name to router node.
        """
        self._log('setting up IBGP (Route Reflector) for as{}...'.format(asn))

        all_rr_names: Set[str] = set()

        for cluster_id, (rr_names, client_names) in clusters.items():
            all_rr_names.update(rr_names)

            for rr_name in sorted(rr_names):
                if rr_name not in routers_map:
                    continue

                rr_node = routers_map[rr_name]
                rr_address = rr_node.getLoopbackAddress()

                for client_name in sorted(client_names):
                    if client_name not in routers_map:
                        continue

                    client_node = routers_map[client_name]
                    client_address = client_node.getLoopbackAddress()
                    install_router_bgp_session(
                        rr_node,
                        {
                            "name": "Ibgp_rr_client_{}".format(client_name),
                            "kind": "ibgp",
                            "local_address": str(rr_address),
                            "local_asn": asn,
                            "peer_address": str(client_address),
                            "peer_asn": asn,
                            "export_policy": "all",
                            "next_hop_self": False,
                            "igp_table": igp_table,
                            "passive": True,
                            "route_reflector_client": True,
                            "route_reflector_cluster_id": cluster_id,
                            "hold_time": self.__hold_time,
                            "keepalive_time": self.__keepalive_time,
                        },
                    )
                    install_router_bgp_session(
                        client_node,
                        {
                            "name": "Ibgp_rr_{}".format(rr_name),
                            "kind": "ibgp",
                            "local_address": str(client_address),
                            "local_asn": asn,
                            "peer_address": str(rr_address),
                            "peer_asn": asn,
                            "export_policy": "all",
                            "next_hop_self": True,
                            "igp_table": igp_table,
                            "hold_time": self.__hold_time,
                            "keepalive_time": self.__keepalive_time,
                        },
                    )

                    self._log(
                        'adding RR peering: {}(RR) <-> {}(client) cluster {} (as{})'.format(
                            rr_name, client_name, cluster_id, asn
                        )
                    )

        sorted_rrs = sorted(
            [routers_map[name] for name in all_rr_names if name in routers_map],
            key = lambda router: router.getName()
        )

        for i in range(len(sorted_rrs)):
            for j in range(i + 1, len(sorted_rrs)):
                node_a = sorted_rrs[i]
                node_b = sorted_rrs[j]

                install_router_bgp_session(
                    node_a,
                    {
                        "name": "Ibgp_rr_mesh_{}".format(node_b.getName()),
                        "kind": "ibgp",
                        "local_address": str(node_a.getLoopbackAddress()),
                        "local_asn": asn,
                        "peer_address": str(node_b.getLoopbackAddress()),
                        "peer_asn": asn,
                        "export_policy": "all",
                        "next_hop_self": False,
                        "igp_table": igp_table,
                        "hold_time": self.__hold_time,
                        "keepalive_time": self.__keepalive_time,
                    },
                )
                install_router_bgp_session(
                    node_b,
                    {
                        "name": "Ibgp_rr_mesh_{}".format(node_a.getName()),
                        "kind": "ibgp",
                        "local_address": str(node_b.getLoopbackAddress()),
                        "local_asn": asn,
                        "peer_address": str(node_a.getLoopbackAddress()),
                        "peer_asn": asn,
                        "export_policy": "all",
                        "next_hop_self": False,
                        "igp_table": igp_table,
                        "hold_time": self.__hold_time,
                        "keepalive_time": self.__keepalive_time,
                    },
                )

                self._log(
                    'adding RR mesh peering: {} <-> {} (as{})'.format(
                        node_a.getName(), node_b.getName(), asn
                    )
                )

    def _render_full_mesh_mode(self, asn: int, routers: List[Node], igp_table: str = "t_ospf"):
        """!
        @brief Render the legacy full-mesh iBGP sessions for one AS.

        @param asn AS number being rendered.
        @param routers routers participating in the legacy iBGP mesh.
        """
        self._log('setting up IBGP (Full Mesh) for as{}...'.format(asn))
        allowed_names = {router.getName() for router in routers}

        for local in routers:
            self._log('setting up IBGP peering on as{}/{}...'.format(asn, local.getName()))

            remotes = []
            self.__dfs(local, remotes)

            n = 1
            for remote in remotes:
                if local == remote:
                    continue
                if remote.getName() not in allowed_names:
                    continue

                laddr = local.getLoopbackAddress()
                raddr = remote.getLoopbackAddress()
                install_router_bgp_session(
                    local,
                    {
                        "name": "ibgp{}".format(n),
                        "kind": "ibgp",
                        "local_address": str(laddr),
                        "local_asn": asn,
                        "peer_address": str(raddr),
                        "peer_asn": asn,
                        "export_policy": "all",
                        "next_hop_self": False,
                        "igp_table": igp_table,
                        "hold_time": self.__hold_time,
                        "keepalive_time": self.__keepalive_time,
                    },
                )

                n += 1

                self._log('adding peering: {} <-> {} (ibgp, as{})'.format(laddr, raddr, asn))

    def render(self, emulator: Emulator):
        pass

    def _doCreateGraphs(self, emulator: Emulator):
        base: Base = emulator.getRegistry().get('seedemu', 'layer', 'Base')
        for asn in base.getAsns():
            asobj = base.getAutonomousSystem(asn)
            if int(asn) in self.__masked:
                asobj.setIbgpMode(IBGP_MODE_DISABLED)
            asobj.completeIbgpSetup()
            mode = asobj.getIbgpMode()
            if mode == IBGP_MODE_DISABLED: continue
            asobj.createGraphs(emulator)
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            ibgpgraph = self._addGraph('AS{}: iBGP sessions'.format(asn), False)
            ibgpgraph.copy(l2graph)
            for edge in ibgpgraph.edges:
                edge.style = 'dotted'

            scope = ScopedRegistry(str(asn), emulator.getRegistry())
            rtrs = scope.getByType('rnode').copy()
            routers_map: Dict[str, Node] = {router.getName(): router for router in rtrs}
            disabled = {name for name, router in routers_map.items() if self.__is_ibgp_disabled(router)}
            active_names = asobj.getIbgpParticipants() - disabled

            if mode == IBGP_MODE_ROUTE_REFLECTOR:
                clusters = asobj._aggregateBgpClusters()
                all_rrs: Set[str] = set()
                for _cluster_id, (rr_names, client_names) in clusters.items():
                    all_rrs.update(rr_names)
                    for rr_name in rr_names:
                        for client_name in client_names:
                            if rr_name in active_names and client_name in active_names:
                                ibgpgraph.addEdge(
                                    'Router: {}'.format(rr_name),
                                    'Router: {}'.format(client_name),
                                    style = 'solid'
                                )
                rtrs = [
                    routers_map[name]
                    for name in sorted(all_rrs)
                    if name in routers_map and name in active_names
                ]
            else:
                rtrs = [routers_map[name] for name in sorted(active_names) if name in routers_map]

            while len(rtrs) > 0:
                a = rtrs.pop()
                for b in rtrs:
                    ibgpgraph.addEdge('Router: {}'.format(a.getName()), 'Router: {}'.format(b.getName()), style = 'solid')
            

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'IbgpLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'Masked ASes:\n'

        indent += 4
        for asn in self.__masked:
            out += ' ' * indent
            out += '{}\n'.format(asn)

        return out
