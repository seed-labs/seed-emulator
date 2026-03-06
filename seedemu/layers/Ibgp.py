from __future__ import annotations
from seedemu.core.enums import NetworkType, NodeRole
from .Base import Base
from seedemu.core import ScopedRegistry, Node, Graphable, Emulator, Layer
from typing import List, Set, Dict

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

    def __init__(self):
        """!
        @brief Ibgp (iBGP) layer constructor.
        """
        super().__init__()
        self.__masked = set()
        self.addDependency('Ospf', False, False)

    def __is_rr(self, node: Node) -> bool:
        return hasattr(node, "isRouteReflector") and bool(node.isRouteReflector())

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
                    # RR peers with all other routers in its component (RR<->RR, RR<->client).
                    peers = [r for r in remotes if r != local]
                else:
                    # Client peers only with RRs in its component.
                    peers = component_rrs

                n = 1
                for remote in peers:
                    if local == remote:
                        continue

                    laddr = local.getLoopbackAddress()
                    raddr = remote.getLoopbackAddress()
                    local.addTable('t_bgp')
                    local.addTablePipe('t_bgp')
                    local.addTablePipe('t_direct', 't_bgp')
                    template_key = 'ibgp_peer'
                    if (not use_full_mesh) and local_is_rr and (not self.__is_rr(remote)):
                        template_key = 'ibgp_rr_client'
                    local.addProtocol('bgp', 'ibgp{}'.format(n), IbgpFileTemplates[template_key].format(
                        localAddress = laddr,
                        peerAddress = raddr,
                        asn = asn
                    ))

                    n += 1

                    if template_key == 'ibgp_rr_client':
                        self._log('adding peering: {} <-> {} (ibgp-rr-client, as{})'.format(laddr, raddr, asn))
                    else:
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
            rtrs_set = set(rtrs)

            def local_router_neighbors(node: Node) -> List[Node]:
                neighs: List[Node] = []
                for iface in node.getInterfaces():
                    net = iface.getNet()
                    if net.getType() != NetworkType.Local:
                        continue
                    for neigh in net.getAssociations():
                        if neigh not in rtrs_set:
                            continue
                        role = neigh.getRole()
                        if role not in (NodeRole.Router, NodeRole.BorderRouter, NodeRole.OpenVpnRouter):
                            continue
                        neighs.append(neigh)
                return neighs

            # Mirror the render() topology:
            # - component without RR => full-mesh within component
            # - component with RR(s) => RR mesh + clients->RR star within component
            unseen = set(rtrs)
            while unseen:
                start = unseen.pop()
                stack = [start]
                component: Set[Node] = set()

                while stack:
                    cur = stack.pop()
                    if cur in component:
                        continue
                    component.add(cur)
                    for neigh in local_router_neighbors(cur):
                        if neigh not in component:
                            stack.append(neigh)

                unseen -= component

                comp_list = sorted(component, key=lambda r: r.getName())
                comp_rrs = [r for r in comp_list if self.__is_rr(r)]

                if len(comp_rrs) == 0:
                    for i, a in enumerate(comp_list):
                        for b in comp_list[i + 1 :]:
                            ibgpgraph.addEdge(
                                'Router: {}'.format(a.getName()),
                                'Router: {}'.format(b.getName()),
                                style='solid',
                            )
                    continue

                # RR<->RR mesh
                for i, a in enumerate(comp_rrs):
                    for b in comp_rrs[i + 1 :]:
                        ibgpgraph.addEdge(
                            'Router: {}'.format(a.getName()),
                            'Router: {}'.format(b.getName()),
                            style='solid',
                        )

                # client<->RR star
                comp_clients = [r for r in comp_list if r not in comp_rrs]
                for client in comp_clients:
                    for rr in comp_rrs:
                        ibgpgraph.addEdge(
                            'Router: {}'.format(client.getName()),
                            'Router: {}'.format(rr.getName()),
                            style='solid',
                        )
            

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
