from __future__ import annotations
from seedemu.core.enums import NetworkType, NodeRole
from .Base import Base
from seedemu.core import ScopedRegistry, Node, Graphable, Emulator, Layer
from typing import List, Set, Dict, Tuple

IbgpFileTemplates: Dict[str, str] = {}

IbgpFileTemplates['ibgp_peer'] = '''
    #debug {{states}};
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table t_ospf;
    }};
    local {localAddress} as {asn};
    neighbor {peerAddress} as {asn};
'''

# 1. 普通 Peer 模板 (用于 Client->RR, RR<->RR, 或者 Full Mesh)
IbgpFileTemplates['ibgp_client'] = '''
    #debug {{states}};
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

# 2. RR 服务端模板 (用于 RR->Client)
# K3s phased startup keeps matching on the senior protocol names below, so the
# Ibgp_* naming style must stay stable unless the runtime helper is updated too.
IbgpFileTemplates['ibgp_rr_server'] = '''
    #debug {{states}};
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

    This layer automatically setup full mesh peering between routers within AS.
    """
    __masked: Set[int]

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        super().__init__()
        self.__masked = set()
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
            if asn in self.__masked: continue

            self._log('setting up IBGP peering for as{}...'.format(asn))
            routers: List[Node] = ScopedRegistry(str(asn), reg).getByType('rnode')
            routers_map: Dict[str, Node] = {r.getName(): r for r in routers}

            as_obj = base.getAutonomousSystem(asn)
            clusters = as_obj._aggregateBgpClusters()
            has_rr = any(rrs for rrs, _ in clusters.values())
            if has_rr:
                self._render_rr_mode(asn, clusters, routers_map)
            else:
                self._render_full_mesh_mode(asn, routers)
    
    def _render_rr_mode(self, asn: int, clusters: Dict[str, Tuple[List[str], List[str]]], routers_map: Dict[str, Node]):
        """ RR 模式渲染逻辑 """
        self._log(f'setting up IBGP (Route Reflector) for as{asn}...')

        # 用于收集全网所有 RR，做最后的互联
        all_rr_names: Set[str] = set()

        # --- A. 处理每个 Cluster 内部 (Hub-and-Spoke) ---
        for cluster_id, (rr_names, client_names) in clusters.items():
            # 记录 RR
            all_rr_names.update(rr_names)

            # 遍历该 Cluster 的所有 RR
            for rr_name in rr_names:
                if rr_name not in routers_map: continue
                rr_node = routers_map[rr_name]
                rr_node.addTable('t_bgp')
                rr_node.addTablePipe('t_bgp')
                rr_node.addTablePipe('t_direct', 't_bgp')
                laddr = rr_node.getLoopbackAddress()

                # 遍历该 Cluster 的所有 Client
                for client_name in client_names:
                    if client_name not in routers_map: continue
                    client_node = routers_map[client_name]
                    
                    client_node.addTable('t_bgp')
                    client_node.addTablePipe('t_bgp')
                    client_node.addTablePipe('t_direct', 't_bgp')
                    raddr = client_node.getLoopbackAddress()

                    # 1. 配置 RR 端 (Server: 开启反射)
                    rr_node.addProtocol('bgp', f'Ibgp_to_cli_{client_name}', IbgpFileTemplates['ibgp_rr_server'].format(
                        localAddress=laddr, peerAddress=raddr, asn=asn, clusterId=cluster_id
                    ))

                    # 2. 配置 Client 端 (Peer: 普通连接)
                    client_node.addProtocol('bgp', f'Ibgp_to_rr_{rr_name}', IbgpFileTemplates['ibgp_client'].format(
                        localAddress=raddr, peerAddress=laddr, asn=asn
                    ))
                    
                    self._log(f'adding RR peering: {rr_name}(RR) <-> {client_name}(Client) cluster {cluster_id}')

        # --- B. 处理 RR 之间的全互联 (RR Full Mesh) ---
        # 获取所有 RR 节点并排序
        sorted_rrs = sorted([routers_map[name] for name in all_rr_names if name in routers_map], key=lambda x: x.getName())

        for i in range(len(sorted_rrs)):
            for j in range(i + 1, len(sorted_rrs)):
                node_a = sorted_rrs[i]
                node_b = sorted_rrs[j]
                
                node_a.addTable('t_bgp')
                node_a.addTablePipe('t_bgp')
                node_a.addTablePipe('t_direct', 't_bgp')

                node_b.addTable('t_bgp')
                node_b.addTablePipe('t_bgp')
                node_b.addTablePipe('t_direct', 't_bgp')

                # 双向建立普通 Peer 连接
                node_a.addProtocol('bgp', f'Ibgp_mesh_{node_b.getName()}', IbgpFileTemplates['ibgp_peer'].format(
                    localAddress=node_a.getLoopbackAddress(), peerAddress=node_b.getLoopbackAddress(), asn=asn
                ))
                node_b.addProtocol('bgp', f'Ibgp_mesh_{node_a.getName()}', IbgpFileTemplates['ibgp_peer'].format(
                    localAddress=node_b.getLoopbackAddress(), peerAddress=node_a.getLoopbackAddress(), asn=asn
                ))
                self._log(f'adding RR Mesh: {node_a.getName()} <-> {node_b.getName()}')

    def _render_full_mesh_mode(self, asn: int, routers_list: List[Node]):
        """ 原有的全互联逻辑 (保留 DFS) """
        self._log(f'setting up IBGP (Full Mesh) for as{asn}...')
        
        for local in routers_list:
            remotes = []
            self.__dfs(local, remotes)

            n = 1
            for remote in remotes:
                if local == remote: continue
                
                laddr = local.getLoopbackAddress()
                raddr = remote.getLoopbackAddress()
                local.addTable('t_bgp')
                local.addTablePipe('t_bgp')
                local.addTablePipe('t_direct', 't_bgp')
                local.addProtocol('bgp', 'Ibgp{}'.format(n), IbgpFileTemplates['ibgp_peer'].format(
                    localAddress = laddr,
                    peerAddress = raddr,
                    asn = asn
                ))
                n += 1
                self._log('adding peering: {} <-> {} (ibgp, as{})'.format(laddr, raddr, asn))

    def _doCreateGraphs(self, emulator: Emulator):
        base: Base = emulator.getRegistry().get('seedemu', 'layer', 'Base')
        for asn in base.getAsns():
            if asn in self.__masked: continue
            asobj = base.getAutonomousSystem(asn)
            asobj.createGraphs(emulator)
            l2graph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asn))
            ibgpgraph = self._addGraph('AS{}: iBGP sessions'.format(asn), False)
            ibgpgraph.copy(l2graph)
            for edge in ibgpgraph.edges:
                edge.style = 'dotted'

            rtrs = ScopedRegistry(str(asn), emulator.getRegistry()).getByType('rnode').copy()
            clusters = asobj._aggregateBgpClusters()
            has_rr = any(rrs for rrs, _ in clusters.values())

            if has_rr:
                all_rr_names: Set[str] = set()
                for _, (rr_names, client_names) in clusters.items():
                    sorted_rr_names = sorted(rr_names)
                    sorted_client_names = sorted(client_names)
                    all_rr_names.update(sorted_rr_names)
                    for rr_name in sorted_rr_names:
                        for client_name in sorted_client_names:
                            ibgpgraph.addEdge(
                                'Router: {}'.format(rr_name),
                                'Router: {}'.format(client_name),
                                style='solid'
                            )

                sorted_rr_names = sorted(all_rr_names)
                while len(sorted_rr_names) > 0:
                    rr_name = sorted_rr_names.pop()
                    for peer_rr_name in sorted_rr_names:
                        ibgpgraph.addEdge(
                            'Router: {}'.format(rr_name),
                            'Router: {}'.format(peer_rr_name),
                            style='solid'
                        )
            else:
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
