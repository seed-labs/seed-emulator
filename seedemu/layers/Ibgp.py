from __future__ import annotations
from seedemu.core.enums import NetworkType, NodeRole
from .Base import Base
from seedemu.core import ScopedRegistry, Node, Graphable, Emulator, Layer
from typing import List, Set, Dict, Tuple

IbgpFileTemplates: Dict[str, str] = {}

IbgpFileTemplates['ibgp_peer'] = '''
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
'''

IbgpFileTemplates['ibgp_rr_client'] = '''
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
    rr client;
'''

IbgpFileTemplates['ibgp_client'] = '''
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
        next hop self;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
'''

IbgpFileTemplates['ibgp_rr_server'] = '''
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
    rr client;
    rr cluster id {clusterId};
'''


class Ibgp(Layer, Graphable):
    """!
    @brief The Ibgp (iBGP) layer.

    This layer sets up iBGP peering between routers within an AS.

    Default behavior is full-mesh iBGP. If one or more routers in an AS are
    marked as route reflectors via Router.makeRouteReflector(), iBGP sessions
    will be configured in an RR topology (clients peer only with RRs; RRs mesh
    with each other).
    """
    __masked: Set[int]
    __reflection_mode: str

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        super().__init__()
        self.__masked = set()
        self.__reflection_mode = 'simple'
        self.addDependency('Ospf', False, False)

    def setReflectionMode(self, mode: str) -> Ibgp:
        """!
        @brief Set iBGP reflection mode.

        @param mode one of: simple, clustered.
        @returns self, for chaining API calls.
        """
        assert mode in ('simple', 'clustered'), 'reflection mode must be simple or clustered'
        self.__reflection_mode = mode

        return self

    def getReflectionMode(self) -> str:
        """!
        @brief Get current iBGP reflection mode.

        @returns reflection mode string.
        """
        return self.__reflection_mode

    def __is_rr(self, node: Node) -> bool:
        return hasattr(node, 'isRouteReflector') and bool(node.isRouteReflector())

    def __ensure_bgp_tables(self, node: Node):
        node.addTable('t_bgp')
        node.addTablePipe('t_bgp')
        node.addTablePipe('t_direct', 't_bgp')

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
                if role not in (NodeRole.Router, NodeRole.BorderRouter, NodeRole.OpenVpnRouter):
                    continue

                self.__dfs(neigh, visited, net.getName())

    def __local_router_neighbors(self, node: Node, routers: Set[Node]) -> List[Node]:
        neighs: List[Node] = []
        for iface in node.getInterfaces():
            net = iface.getNet()
            if net.getType() != NetworkType.Local:
                continue
            for neigh in net.getAssociations():
                if neigh not in routers:
                    continue
                role = neigh.getRole()
                if role not in (NodeRole.Router, NodeRole.BorderRouter, NodeRole.OpenVpnRouter):
                    continue
                neighs.append(neigh)
        return neighs

    def __component_sets(self, routers: List[Node]) -> List[Set[Node]]:
        router_set = set(routers)
        unseen = set(routers)
        components: List[Set[Node]] = []

        while unseen:
            start = unseen.pop()
            stack = [start]
            component: Set[Node] = set()

            while stack:
                cur = stack.pop()
                if cur in component:
                    continue
                component.add(cur)
                for neigh in self.__local_router_neighbors(cur, router_set):
                    if neigh not in component:
                        stack.append(neigh)

            unseen -= component
            components.append(component)

        return components

    def __render_simple(self, asn: int, routers: List[Node]):
        as_has_rr = any(self.__is_rr(r) for r in routers)

        for local in routers:
            self._log('setting up IBGP peering on as{}/{}...'.format(asn, local.getName()))

            remotes = []
            self.__dfs(local, remotes)

            local_is_rr = self.__is_rr(local)
            component_rrs = [r for r in remotes if self.__is_rr(r)]
            use_full_mesh = (not as_has_rr) or ((not local_is_rr) and len(component_rrs) == 0)

            if use_full_mesh:
                peers = [r for r in remotes if r != local]
            elif local_is_rr:
                peers = [r for r in remotes if r != local]
            else:
                peers = component_rrs

            n = 1
            for remote in peers:
                if local == remote:
                    continue

                laddr = local.getLoopbackAddress()
                raddr = remote.getLoopbackAddress()
                self.__ensure_bgp_tables(local)
                template_key = 'ibgp_peer'
                if (not use_full_mesh) and local_is_rr and (not self.__is_rr(remote)):
                    template_key = 'ibgp_rr_client'
                local.addProtocol('bgp', 'ibgp{}'.format(n), IbgpFileTemplates[template_key].format(
                    localAddress=laddr,
                    peerAddress=raddr,
                    asn=asn,
                ))

                n += 1

                if template_key == 'ibgp_rr_client':
                    self._log('adding peering: {} <-> {} (ibgp-rr-client, as{})'.format(laddr, raddr, asn))
                else:
                    self._log('adding peering: {} <-> {} (ibgp, as{})'.format(laddr, raddr, asn))

    def __render_clustered(self, asn: int, base: Base, routers: List[Node]):
        asobj = base.getAutonomousSystem(asn)
        clusters = asobj._aggregateBgpClusters() if hasattr(asobj, '_aggregateBgpClusters') else {}
        has_rr = any(len(rrs) > 0 for rrs, _ in clusters.values())
        if not has_rr:
            self.__render_simple(asn, routers)
            return

        routers_map: Dict[str, Node] = {router.getName(): router for router in routers}
        all_rr_names: Set[str] = set()

        for cluster_id, (rr_names, client_names) in clusters.items():
            active_rr_names = [name for name in sorted(rr_names) if name in routers_map]
            active_client_names = [name for name in sorted(client_names) if name in routers_map]
            if len(active_rr_names) == 0:
                continue

            all_rr_names.update(active_rr_names)
            for rr_name in active_rr_names:
                rr_node = routers_map[rr_name]
                self.__ensure_bgp_tables(rr_node)
                laddr = rr_node.getLoopbackAddress()

                for client_name in active_client_names:
                    client_node = routers_map[client_name]
                    self.__ensure_bgp_tables(client_node)
                    raddr = client_node.getLoopbackAddress()
                    rr_node.addProtocol('bgp', f'Ibgp_to_cli_{client_name}', IbgpFileTemplates['ibgp_rr_server'].format(
                        localAddress=laddr,
                        peerAddress=raddr,
                        asn=asn,
                        clusterId=cluster_id,
                    ))
                    client_node.addProtocol('bgp', f'Ibgp_to_rr_{rr_name}', IbgpFileTemplates['ibgp_client'].format(
                        localAddress=raddr,
                        peerAddress=laddr,
                        asn=asn,
                    ))
                    self._log(f'adding RR peering: {rr_name}(RR) <-> {client_name}(Client) cluster {cluster_id}')

        sorted_rrs = sorted(
            [routers_map[name] for name in all_rr_names if name in routers_map],
            key=lambda router: router.getName(),
        )
        for i in range(len(sorted_rrs)):
            for j in range(i + 1, len(sorted_rrs)):
                node_a = sorted_rrs[i]
                node_b = sorted_rrs[j]
                self.__ensure_bgp_tables(node_a)
                self.__ensure_bgp_tables(node_b)
                node_a.addProtocol('bgp', f'Ibgp_mesh_{node_b.getName()}', IbgpFileTemplates['ibgp_peer'].format(
                    localAddress=node_a.getLoopbackAddress(),
                    peerAddress=node_b.getLoopbackAddress(),
                    asn=asn,
                ))
                node_b.addProtocol('bgp', f'Ibgp_mesh_{node_a.getName()}', IbgpFileTemplates['ibgp_peer'].format(
                    localAddress=node_b.getLoopbackAddress(),
                    peerAddress=node_a.getLoopbackAddress(),
                    asn=asn,
                ))
                self._log(f'adding RR Mesh: {node_a.getName()} <-> {node_b.getName()}')

    def __graph_add_edge(self, ibgpgraph, seen_edges: Set[Tuple[str, str]], left: str, right: str):
        edge = tuple(sorted((left, right)))
        if edge in seen_edges:
            return
        seen_edges.add(edge)
        ibgpgraph.addEdge(left, right, style='solid')

    def __create_graph_simple(self, emulator: Emulator, ibgpgraph, asn: int):
        seen_edges: Set[Tuple[str, str]] = set()
        routers = ScopedRegistry(str(asn), emulator.getRegistry()).getByType('rnode').copy()
        for component in self.__component_sets(routers):
            comp_list = sorted(component, key=lambda router: router.getName())
            comp_rrs = [router for router in comp_list if self.__is_rr(router)]

            if len(comp_rrs) == 0:
                for idx, node_a in enumerate(comp_list):
                    for node_b in comp_list[idx + 1:]:
                        self.__graph_add_edge(
                            ibgpgraph,
                            seen_edges,
                            'Router: {}'.format(node_a.getName()),
                            'Router: {}'.format(node_b.getName()),
                        )
                continue

            for idx, node_a in enumerate(comp_rrs):
                for node_b in comp_rrs[idx + 1:]:
                    self.__graph_add_edge(
                        ibgpgraph,
                        seen_edges,
                        'Router: {}'.format(node_a.getName()),
                        'Router: {}'.format(node_b.getName()),
                    )

            for client in comp_list:
                if client in comp_rrs:
                    continue
                for rr in comp_rrs:
                    self.__graph_add_edge(
                        ibgpgraph,
                        seen_edges,
                        'Router: {}'.format(client.getName()),
                        'Router: {}'.format(rr.getName()),
                    )

    def __create_graph_clustered(self, emulator: Emulator, base: Base, ibgpgraph, asn: int):
        asobj = base.getAutonomousSystem(asn)
        clusters = asobj._aggregateBgpClusters() if hasattr(asobj, '_aggregateBgpClusters') else {}
        routers = ScopedRegistry(str(asn), emulator.getRegistry()).getByType('rnode').copy()
        routers_map: Dict[str, Node] = {router.getName(): router for router in routers}
        seen_edges: Set[Tuple[str, str]] = set()
        has_rr = any(len(rrs) > 0 for rrs, _ in clusters.values())

        if not has_rr:
            self.__create_graph_simple(emulator, ibgpgraph, asn)
            return

        all_rr_names: Set[str] = set()
        for _, (rr_names, client_names) in clusters.items():
            rr_nodes = [routers_map[name] for name in sorted(rr_names) if name in routers_map]
            client_nodes = [routers_map[name] for name in sorted(client_names) if name in routers_map]
            all_rr_names.update(node.getName() for node in rr_nodes)

            for idx, node_a in enumerate(rr_nodes):
                for node_b in rr_nodes[idx + 1:]:
                    self.__graph_add_edge(
                        ibgpgraph,
                        seen_edges,
                        'Router: {}'.format(node_a.getName()),
                        'Router: {}'.format(node_b.getName()),
                    )

            for client in client_nodes:
                for rr in rr_nodes:
                    self.__graph_add_edge(
                        ibgpgraph,
                        seen_edges,
                        'Router: {}'.format(client.getName()),
                        'Router: {}'.format(rr.getName()),
                    )

        rr_nodes = [routers_map[name] for name in sorted(all_rr_names) if name in routers_map]
        for idx, node_a in enumerate(rr_nodes):
            for node_b in rr_nodes[idx + 1:]:
                self.__graph_add_edge(
                    ibgpgraph,
                    seen_edges,
                    'Router: {}'.format(node_a.getName()),
                    'Router: {}'.format(node_b.getName()),
                )

    def getName(self) -> str:
        return 'Ibgp'

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

    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()
        base: Base = reg.get('seedemu', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked:
                continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn), reg).getByType('rnode')
            if self.__reflection_mode == 'clustered':
                self.__render_clustered(asn, base, routers)
            else:
                self.__render_simple(asn, routers)

    def _doCreateGraphs(self, emulator: Emulator):
        base: Base = emulator.getRegistry().get('seedemu', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked:
                continue
            asobj = base.getAutonomousSystem(asn)
            asobj.createGraphs(emulator)
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            ibgpgraph = self._addGraph('AS{}: iBGP sessions'.format(asn), False)
            ibgpgraph.copy(l2graph)
            for edge in ibgpgraph.edges:
                edge.style = 'dotted'

            if self.__reflection_mode == 'clustered':
                self.__create_graph_clustered(emulator, base, ibgpgraph, asn)
            else:
                self.__create_graph_simple(emulator, ibgpgraph, asn)

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
