from seedemu.core import (ScopedRegistry, Node, Interface, Network, Emulator,
                          Layer, Router, BaseSystem,
                          promote_to_real_world_router)
from seedemu.core.enums import NetworkType
from typing import Dict, List, Set, Tuple
from ipaddress import IPv4Network

from ._bgp_metadata import (
    BGP_EXPORT_LOCAL_AND_CUSTOMER,
    BGP_KIND_IBGP,
    get_bgp_backend,
    get_bgp_sessions,
    get_ospf_interface_intents,
    has_bgp_connected_export,
)
from .routing_templates import BirdFileTemplates, FrrFileTemplates

BIRD_BGP_BOOTSTRAPPED_ATTR = "__routing_bird_bgp_bootstrapped"
BIRD_CONNECTED_EXPORT_RENDERED_ATTR = "__routing_bird_connected_export_rendered"

def _session_route_map_name(prefix: str, session_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(session_name or "session"))
    return f"{prefix}_{safe}"[:64]


def _render_frr_session_route_maps(local_asn: int, sessions: List[Dict]) -> Tuple[str, Dict[str, Dict[str, str]]]:
    body: List[str] = []
    map_names: Dict[str, Dict[str, str]] = {}
    community_map = {
        "LOCAL_COMM": f"{local_asn}:0:0",
        "CUSTOMER_COMM": f"{local_asn}:1:0",
        "PEER_COMM": f"{local_asn}:2:0",
        "PROVIDER_COMM": f"{local_asn}:3:0",
    }

    for session in sessions:
        name = str(session.get("name") or "session")
        import_name = ""
        import_community = str(session.get("import_community") or "").strip()
        local_pref = session.get("local_pref")
        export_policy = str(session.get("export_policy") or "all").strip()

        if import_community and local_pref is not None:
            import_name = _session_route_map_name("RM_IMPORT", name)
            body.append(
                FrrFileTemplates["import_route_map"].format(
                    name=import_name,
                    community=community_map.get(import_community, import_community),
                    local_pref=int(local_pref),
                )
            )

        export_name = _session_route_map_name("RM_EXPORT", name)
        if export_policy == "local_and_customer":
            body.append(FrrFileTemplates["export_route_map_local_customer"].format(name=export_name))
        else:
            body.append(FrrFileTemplates["export_route_map_all"].format(name=export_name))

        map_names[name] = {"import": import_name, "export": export_name}

    return "".join(body), map_names


def _bird_import_clause(session: Dict) -> str:
    if session["import_community"] and session["local_pref"] is not None:
        return (
            "filter {\n"
            f"            bgp_large_community.add({session['import_community']});\n"
            f"            bgp_local_pref = {int(session['local_pref'])};\n"
            "            accept;\n"
            "        }"
        )
    return "all"


def _bird_export_clause(session: Dict) -> str:
    if session["export_policy"] == BGP_EXPORT_LOCAL_AND_CUSTOMER:
        return "where bgp_large_community ~ [LOCAL_COMM, CUSTOMER_COMM]"
    return "all"


def _render_bird_protocol_body(session: Dict) -> str:
    if session["route_server_client"]:
        return BirdFileTemplates["rs_peer"].format(
            localAddress=session["local_address"],
            localAsn=session["local_asn"],
            peerAddress=session["peer_address"],
            peerAsn=session["peer_asn"],
        )
    if session["kind"] == BGP_KIND_IBGP:
        return BirdFileTemplates["ibgp_peer"].format(
            localAddress=session["local_address"],
            localAsn=session["local_asn"],
            peerAddress=session["peer_address"],
            peerAsn=session["peer_asn"],
            igpTable=session["igp_table"],
        )
    next_hop_self_clause = "        next hop self;\n" if session["next_hop_self"] else ""
    return BirdFileTemplates["router_peer"].format(
        importClause=_bird_import_clause(session),
        exportClause=_bird_export_clause(session),
        nextHopSelfClause=next_hop_self_clause,
        localAddress=session["local_address"],
        localAsn=session["local_asn"],
        peerAddress=session["peer_address"],
        peerAsn=session["peer_asn"],
    )


class Routing(Layer):
    """!
    @brief The Routing layer.

    This layer provides routing support for routers and hosts. i.e., (1) install
    BIRD on router nodes and allow BGP/OSPF to work, (2) setup kernel and device
    protocols, and (3) setup default routes for host nodes.

    When this layer is rendered, two new methods will be added to the router
    node and can be used by other layers: (1) addProtocol: add new protocol
    block to BIRD, and (2) addTable: add new routing table to BIRD.

    This layer also assign loopback address for iBGP/LDP, etc., for other
    protocols to use later and as router id.
    """

    _loopback_assigner: IPv4Network
    _loopback_pos: int

    def __init__(self, loopback_range: str = '10.0.0.0/16'):
        """!
        @brief Routing layer constructor.

        @param loopback_range (optional) network range for assigning loopback
        IP addresses.
        """
        super().__init__()
        self._loopback_assigner = IPv4Network(loopback_range)
        self._loopback_pos = 1
        self.addDependency('Base', False, False)
        self.addDependency('Ospf', True, True)
        self.addDependency('Ibgp', True, True)
        self.addDependency('Ebgp', True, True)

    def getName(self) -> str:
        return "Routing"

    def _installBird(self, node: Node):
        """!
        @brief Install bird on node, and handle the bug.
        """
        # addBuildCommand and addSoftware lines are needed when user wants to use custom image.
        node.addBuildCommand('mkdir -p /usr/share/doc/bird2/examples/')
        node.addBuildCommand('touch /usr/share/doc/bird2/examples/bird.conf')
        node.addSoftware('bird2')

        self._ensureRouterBaseSystem(node)

    def _ensureRouterBaseSystem(self, node: Node):
        """!
        @brief Ensure the node uses the router base system even when BIRD is not installed.
        """

        base = node.getBaseSystem()
        if not BaseSystem.doesAContainB(base,BaseSystem.SEEDEMU_ROUTER) and base !=BaseSystem.SEEDEMU_ROUTER:
            node.setBaseSystem(BaseSystem.SEEDEMU_ROUTER)

    def _configure_bird_rs(self, rs_node: Node):
        rs_node.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
        rs_node.appendStartCommand('bird -d', True)
        self._log("Bootstrapping bird.conf for RS {}...".format(rs_node.getName()))

        rs_ifaces = rs_node.getInterfaces()
        assert len(rs_ifaces) == 1, "rs node {} has != 1 interfaces".format(rs_node.getName())

        rs_iface = rs_ifaces[0]

        assert issubclass(rs_node.__class__, Router)
        rs_node.setBorderRouter(True)
        rs_node.setFile("/etc/bird/bird.conf", BirdFileTemplates["rs_base"].format(
            routerId = rs_iface.getAddress()
        ))

    def _configure_rs(self, rs_node: Node):
        backend = get_bgp_backend(rs_node)
        if backend == "bird":
            self._configure_bird_rs(rs_node)
        elif backend == "frr":
            raise NotImplementedError(
                "FRR route-server nodes are not supported yet; use BIRD route servers"
            )
        else:
            raise ValueError(f"unsupported routing backend for route server: {backend}")

    def _configure_bird_router(self, rnode: Router):
        ifaces = ''
        has_localnet = False
        for iface in rnode.getInterfaces():
            net = iface.getNet()
            if net.isDirect():
                has_localnet = True
                ifaces += BirdFileTemplates["router_direct_interface"].format(
                    interfaceName = net.getName()
                )
        rnode.setFile("/etc/bird/bird.conf",
            BirdFileTemplates["router_base"].format(
              routerId = rnode.getLoopbackAddress()))
        if get_bgp_backend(rnode) == "bird":
            rnode.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
            rnode.appendStartCommand('bird -d', True)
        if has_localnet:
            rnode.addProtocol('direct', 'local_nets',
                              BirdFileTemplates["direct_protocol"].format(interfaces = ifaces))

    def _ensure_bird_bgp_base(self, router: Router):
        if not router.getAttribute(BIRD_BGP_BOOTSTRAPPED_ATTR, False):
            router.setAttribute(BIRD_BGP_BOOTSTRAPPED_ATTR, True)
            router.appendFile(
                "/etc/bird/bird.conf",
                BirdFileTemplates["bgp_commons"].format(localAsn=router.getAsn()),
            )
        router.addTable("t_bgp")
        router.addTablePipe("t_bgp")
        if has_bgp_connected_export(router) and not router.getAttribute(BIRD_CONNECTED_EXPORT_RENDERED_ATTR, False):
            router.addTablePipe(
                "t_direct",
                "t_bgp",
                exportFilter=BirdFileTemplates["connected_export_filter"],
            )
            router.setAttribute(BIRD_CONNECTED_EXPORT_RENDERED_ATTR, True)

    def _render_bird_sessions(self, router: Router, include_bgp_base: bool = True):
        if router.getAttribute("__routing_bird_sessions_rendered", False):
            return
        sessions = get_bgp_sessions(router)
        if not sessions:
            return
        if include_bgp_base or any(not session["route_server_client"] for session in sessions):
            self._ensure_bird_bgp_base(router)
        for session in sessions:
            router.addProtocol("bgp", session["name"], _render_bird_protocol_body(session))
        router.setAttribute("__routing_bird_sessions_rendered", True)

    def _render_bird_ospf(self, router: Router):
        if router.getAttribute("__routing_bird_ospf_rendered", False):
            return
        intents = get_ospf_interface_intents(router)
        active = list(intents.get("active", []) or [])
        passive = list(intents.get("passive", []) or [])
        if not active and not passive:
            return
        ospf_interfaces = ""
        for iface_name in passive:
            ospf_interfaces += BirdFileTemplates["ospf_stub_interface"].format(interfaceName=iface_name)
        for iface_name in active:
            ospf_interfaces += BirdFileTemplates["ospf_interface"].format(interfaceName=iface_name)
        router.addTable('t_ospf')
        router.addProtocol('ospf', 'ospf1', BirdFileTemplates["ospf_body"].format(interfaces=ospf_interfaces))
        router.addTablePipe('t_ospf')
        router.setAttribute("__routing_bird_ospf_rendered", True)

    def _render_frr_ospf_block(self, router: Router) -> str:
        body: List[str] = []
        intents = get_ospf_interface_intents(router)
        active_ifaces: List[str] = list(intents.get("active", []) or [])
        passive_ifaces: List[str] = list(intents.get("passive", []) or ["dummy0"])
        if not active_ifaces and not passive_ifaces:
            for iface in router.getInterfaces():
                net = iface.getNet()
                name = str(net.getName())
                if net.getType() == NetworkType.Local:
                    active_ifaces.append(name)
                else:
                    passive_ifaces.append(name)

        seen: Set[str] = set()
        for name in active_ifaces:
            if name in seen:
                continue
            seen.add(name)
            body.append(FrrFileTemplates["ospf_interface_active"].format(interface=name))
        for name in passive_ifaces:
            if name in seen:
                continue
            seen.add(name)
            body.append(FrrFileTemplates["ospf_interface_passive"].format(interface=name))

        body.append(FrrFileTemplates["ospf_router"].format(router_id=str(router.getLoopbackAddress() or "")))
        return "".join(body)

    def _render_frr_bgp_block(self, router: Router, sessions: List[Dict]) -> str:
        local_asn = int(router.getAsn())
        loopback = str(router.getLoopbackAddress() or "")
        route_maps, map_names = _render_frr_session_route_maps(local_asn, sessions)
        body: List[str] = [
            FrrFileTemplates["community_lists"].format(
                local_comm=f"{local_asn}:0:0",
                customer_comm=f"{local_asn}:1:0",
            ),
            route_maps,
            f"router bgp {local_asn}\n",
            f" bgp router-id {loopback}\n",
            " no bgp default ipv4-unicast\n",
            " no bgp ebgp-requires-policy\n",
        ]

        seen_neighbors: Set[str] = set()
        for session in sessions:
            peer_address = str(session.get("peer_address") or "").strip()
            peer_asn = int(session.get("peer_asn") or 0)
            if not peer_address or peer_asn <= 0 or peer_address in seen_neighbors:
                continue
            seen_neighbors.add(peer_address)
            session_name = str(session.get("name") or f"peer_{peer_asn}")
            body.append(f" neighbor {peer_address} remote-as {peer_asn}\n")
            body.append(f" neighbor {peer_address} description {session_name}\n")

        body.append(" !\n")
        body.append(" address-family ipv4 unicast\n")
        if has_bgp_connected_export(router):
            body.append("  redistribute connected route-map RM_CONNECTED_TO_BGP\n")
            body.insert(1, FrrFileTemplates["route_map_connected"].format(local_comm=f"{local_asn}:0:0"))

        for session in sessions:
            peer_address = str(session.get("peer_address") or "").strip()
            if not peer_address:
                continue
            session_name = str(session.get("name") or "")
            names = map_names.get(session_name, {})
            body.append(f"  neighbor {peer_address} activate\n")
            if bool(session.get("next_hop_self")):
                body.append(f"  neighbor {peer_address} next-hop-self\n")
            import_name = str(names.get("import") or "")
            export_name = str(names.get("export") or "")
            if import_name:
                body.append(f"  neighbor {peer_address} route-map {import_name} in\n")
            if export_name:
                body.append(f"  neighbor {peer_address} route-map {export_name} out\n")
        body.append(" exit-address-family\n!\n")
        return "".join(body)

    def _configure_frr_router(self, router: Router):
        router.addSoftware("frr")
        router.setFile(
            "/etc/frr/frr.conf",
            FrrFileTemplates["managed_block"].format(
                hostname=f"as{router.getAsn()}-{router.getName()}",
                body=self._render_frr_ospf_block(router) + self._render_frr_bgp_block(router, get_bgp_sessions(router)),
            ),
        )
        router.setFile("/frr_start", FrrFileTemplates["start_script"])
        router.appendStartCommand("chmod +x /frr_start")
        router.appendStartCommand("/frr_start")

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rs':
                rs_node: Node = obj
                self._ensureRouterBaseSystem(rs_node)
                rs_backend = get_bgp_backend(rs_node)
                if rs_backend == "bird":
                    self._installBird(rs_node)
                elif rs_backend != "frr":
                    raise ValueError(f"unsupported routing backend for route server: {rs_backend}")
                self._configure_rs(rs_node)
            if type == 'rnode':
                rnode: Router = obj
                assert issubclass(rnode.__class__, Router)

                self._log("Setting up loopback interface for AS{} Router {}...".format(scope, name))

                if rnode.getLoopbackAddress() == None:
                    lbaddr = self._loopback_assigner[self._loopback_pos]
                    self._loopback_pos += 1
                else:
                    lbaddr = rnode.getLoopbackAddress()

                rnode.appendStartCommand('ip li add dummy0 type dummy')
                rnode.appendStartCommand('ip li set dummy0 up')
                rnode.appendStartCommand('ip addr add {}/32 dev dummy0'.format(lbaddr))
                rnode.setLabel('loopback_addr', lbaddr)
                rnode.setLoopbackAddress(lbaddr)

                self._log("Preparing routing backend for AS{} Router {}...".format(scope, name))

                r_ifaces = rnode.getInterfaces()
                assert len(r_ifaces) > 0, "router node {}/{} has no interfaces".format(rnode.getAsn(), rnode.getName())

                self._ensureRouterBaseSystem(rnode)
                backend = get_bgp_backend(rnode)
                if backend == "bird":
                    self._installBird(rnode)
                    self._configure_bird_router(rnode)
                elif backend == "frr":
                    self._log("Deferring routing daemon setup for AS{} Router {} (backend={})...".format(
                        scope, name, backend
                    ))
                else:
                    raise ValueError(f"unsupported routing backend for router as{scope}/{name}: {backend}")

    def render(self, emulator: Emulator):
        reg = emulator.getRegistry()

        gateway_constraints = {}
        hit: bool = False
        for ((scope, type, name), obj) in reg.getAll().items():
            # make sure that on each externaly connected net (those with at least one host who requested it)
            #  (I):  there is at least one RealWorldRouter
            #  (II): the RWR is the default gateway of the requesters on this net
            if type == 'net' and obj.getType() == NetworkType.Local:
                if (p := obj.getExternalConnectivityProvider() ):
                   hit |= True
                   rwr_candidates, new_gateway_constraints = p.resolveRWA( emulator, obj)
                   for r in rwr_candidates:
                       r = promote_to_real_world_router(r, False)
                       route = obj.getPrefix()
                       # only for hosts on THIS network ('route') the RWA is provided
                       r.addRealWorldRoute('0.0.0.0/1', str(route))
                       r.addRealWorldRoute('128.0.0.0/1', str(route))
                   for h, gw in new_gateway_constraints.items():
                       assert h not in gateway_constraints, 'multihomed host ?!'
                       gateway_constraints[h] = gw
                   pass
        # don't create it unnecessary
        svc_net = emulator.getServiceNetwork() if hit or (reg.has('seedemu', 'net', '000_svc')) else None

        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rs' or type == 'rnode':
                assert issubclass(obj.__class__, Router), 'routing: render: adding new RS/Router after routing layer configured is not currently supported.'

            if type == 'rs':
                rs_node: Router = obj
                backend = get_bgp_backend(rs_node)
                if backend == "bird":
                    self._render_bird_sessions(rs_node, include_bgp_base=False)
                elif backend == "frr":
                    raise NotImplementedError(
                        "FRR route-server nodes are not supported yet; use BIRD route servers"
                    )
                else:
                    raise ValueError(f"unsupported routing backend for route server: {backend}")

            if type == 'rnode':
                rnode: Router = obj
                if rnode.hasExtension('RealWorldRouter'): # could also be ScionRouter which needs RealWorldAccess

                    # this is an exception - Only for service net (not part of simulation)
                    rnode._Node__joinNetwork(svc_net)
                    [l, b, d] = svc_net.getDefaultLinkProperties()
                    rnode.appendFile('/ifinfo.txt',
                                     '{}:{}:{}:{}:{}\n'.format(svc_net.getName(), svc_net.getPrefix(), l, b, d))

                    self._log("Sealing real-world router as{}/{}...".format(rnode.getAsn(), rnode.getName()))
                    rnode.seal(svc_net)

                backend = get_bgp_backend(rnode)
                if backend == "bird":
                    self._render_bird_ospf(rnode)
                    self._render_bird_sessions(rnode)
                elif backend == "frr":
                    if rnode.getAttribute("__routing_backend_rendered", False):
                        continue
                    self._log("Rendering FRR backend for AS{} Router {}...".format(scope, name))
                    self._configure_frr_router(rnode)
                    rnode.setAttribute("__routing_backend_rendered", True)
                else:
                    raise ValueError(f"unsupported routing backend for router as{scope}/{name}: {backend}")

            if type in ['hnode', 'csnode']:
                hnode: Node = obj
                hifaces: List[Interface] = hnode.getInterfaces()
                assert len(hifaces) == 1, 'Host {} in as{} has != 1 interfaces'.format(name, scope)
                hif = hifaces[0]
                hnet: Network = hif.getNet()
                rif: Interface = None
                candidates = []
                if hnode in gateway_constraints:
                    candidates.append(gateway_constraints[hnode])
                else:
                    cur_scope = ScopedRegistry(scope, reg)
                    candidates = cur_scope.getByType('rnode')


                for router in candidates:
                    if rif != None: break
                    for riface in router.getInterfaces():
                        if riface.getNet() == hnet:
                            rif = riface
                            break

                if rif == None and hnet.getType() == NetworkType.InternetExchange:
                    self._log(
                        "Host {} in as{} is directly attached to IX {}; skipping default route.".format(
                            name, scope, hnet.getName()
                        )
                    )
                    continue
                assert rif != None, 'Host {} in as{} in network {}: no router'.format(name, scope, hnet.getName())
                self._log("Setting default route for host {} ({}) to router {}".format(name, hif.getAddress(), rif.getAddress()))
                hnode.appendStartCommand('ip rou del default 2> /dev/null')
                hnode.appendStartCommand('ip route add default via {} dev {}'.format(rif.getAddress(), rif.getNet().getName()))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RoutingLayer: BIRD 2.0.x\n'

        return out
