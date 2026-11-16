from seedemu.core import (ScopedRegistry, Node, Interface, Network, Emulator,
                          Layer, Router, BaseSystem,
                          promote_to_real_world_router)
from seedemu.core.enums import NetworkType
from typing import Dict, List, Set, Tuple
from ipaddress import IPv4Network
from ._bgp_metadata import (
    BGP_EXPORT_LOCAL_AND_CUSTOMER,
    BGP_BACKEND_BIRD,
    BGP_BACKEND_FRR,
    get_bgp_backend,
    get_bgp_sessions,
    get_mpls_ldp_intent,
    get_ospf_interface_intents,
    get_ospf_timers,
    has_bgp_connected_export,
    ensure_bird_bgp_base,
    render_frr_community,
    render_bird_protocol_body,
)

RoutingFileTemplates: Dict[str, str] = {}

RoutingFileTemplates["rs_bird"] = """\
router id {routerId};
ipv4 table t_direct;
protocol device {{
}}
"""

RoutingFileTemplates["rnode_bird_direct_interface"] = """
    interface "{interfaceName}";
"""

RoutingFileTemplates["rnode_bird"] = """\
router id {routerId};
ipv4 table t_direct;
protocol device {{
}}
protocol kernel {{
    ipv4 {{
        import all;
        export all;
    }};
    learn;
}}
"""

RoutingFileTemplates['rnode_bird_direct'] = """
    ipv4 {{
        table t_direct;
        import all;
    }};
{interfaces}
"""

RoutingFileTemplates['bird_ospf_body'] = """
    ipv4 {{
        table t_ospf;
        import all;
        export all;
    }};
    tick {tick};
    area 0 {{
{interfaces}
    }};
"""

RoutingFileTemplates['bird_ospf_interface'] = """\
        interface "{interfaceName}" {{ hello {hello}; dead {dead}; }};
"""

RoutingFileTemplates['bird_ospf_stub_interface'] = """\
        interface "{interfaceName}" {{ stub; }};
"""

FrrFileTemplates: Dict[str, str] = {}

FrrFileTemplates["managed_block"] = """\
! ===== seedemu-routing-frr begin =====
frr defaults traditional
service integrated-vtysh-config
hostname {hostname}
!
{body}
! ===== seedemu-routing-frr end =====
"""

FrrFileTemplates["start_script"] = """\
#!/bin/bash
set -e
{pre_start}\
sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons
sed -i 's/staticd=no/staticd=yes/' /etc/frr/daemons
{daemons}\
service frr start
"""

FrrFileTemplates["start_daemon"] = """\
sed -i 's/{daemon}=no/{daemon}=yes/' /etc/frr/daemons
"""

FrrFileTemplates["mpls_start"] = """\
mount -o remount rw /proc/sys 2> /dev/null || true
if [ -d /proc/sys/net/mpls ]; then
    echo '{platform_labels}' > /proc/sys/net/mpls/platform_labels || true
    while read -r iface; do
        [ -z "$iface" ] && continue
        [ -e "/proc/sys/net/mpls/conf/$iface/input" ] && echo '1' > "/proc/sys/net/mpls/conf/$iface/input" || true
    done < /mpls_ifaces.txt
fi
"""

FrrFileTemplates["connected_prefix_list"] = """\
ip prefix-list PL_CONNECTED4_TO_BGP seq {seq} permit {prefix}
"""

FrrFileTemplates["route_map_connected"] = """\
route-map RM_CONNECTED_TO_BGP permit 10
 match ip address prefix-list PL_CONNECTED4_TO_BGP
 set large-community {local_comm} additive
 set local-preference 40
!
"""

FrrFileTemplates["community_lists"] = """\
bgp large-community-list standard LC_LOCAL permit {local_comm}
bgp large-community-list standard LC_CUSTOMER permit {customer_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {local_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {customer_comm}
!
"""

FrrFileTemplates["import_route_map"] = """\
route-map {name} permit 10
 set large-community {community} additive
 set local-preference {local_pref}
!
"""

FrrFileTemplates["export_route_map_local_customer"] = """\
route-map {name} permit 10
 match large-community LC_LOCAL_OR_CUSTOMER
!
route-map {name} deny 100
!
"""

FrrFileTemplates["export_route_map_all"] = """\
route-map {name} permit 10
!
"""

FrrFileTemplates["ospf_interface_active"] = """\
interface {interface}
 ip ospf area 0
 ip ospf hello-interval {hello}
 ip ospf dead-interval {dead}
!
"""

FrrFileTemplates["ospf_interface_passive"] = """\
interface {interface}
 ip ospf area 0
 ip ospf passive
!
"""

FrrFileTemplates["ospf_router"] = """\
router ospf
 ospf router-id {router_id}
!
"""

FrrFileTemplates["mpls_config"] = """\
router-id {router_id}
{ospf_interfaces}
mpls ldp
 address-family ipv4
  discovery transport-address {router_id}
{ldp_interfaces}
 exit-address-family
!
router ospf
 redistribute connected
!
"""

FrrFileTemplates["mpls_ospf_interface"] = """\
interface {interface}
 ip ospf area 0
 ip ospf dead-interval minimal hello-multiplier 2
!
"""

FrrFileTemplates["mpls_ldp_interface"] = """\
  interface {interface}
"""


def _frr_map_name(prefix: str, session_id: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(session_id or "session"))
    return "{}_{}".format(prefix, safe)[:64]


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
        @brief Ensure a routing backend keeps the router base system.
        """
        base = node.getBaseSystem()
        if (
            base != BaseSystem.SEEDEMU_ROUTER
            and not base.contains(BaseSystem.SEEDEMU_ROUTER)
        ):
            node.setBaseSystem(BaseSystem.SEEDEMU_ROUTER)

    def _installFrr(self, node: Node):
        """!
        @brief Install FRRouting on node.
        """
        node.addSoftware('frr')
        self._ensureRouterBaseSystem(node)

    def _configure_rs(self, rs_node: Node):
        backend = get_bgp_backend(rs_node)
        rs_ifaces = rs_node.getInterfaces()
        assert len(rs_ifaces) == 1, "rs node {} has != 1 interfaces".format(rs_node.getName())
        rs_iface = rs_ifaces[0]

        assert issubclass(rs_node.__class__, Router)
        rs_node.setBorderRouter(True)
        if backend == BGP_BACKEND_BIRD:
            rs_node.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
            rs_node.appendStartCommand('bird -d', True)
            self._log("Bootstrapping bird.conf for RS {}...".format(rs_node.getName()))
            rs_node.setFile("/etc/bird/bird.conf", RoutingFileTemplates["rs_bird"].format(
                routerId = rs_iface.getAddress()
            ))
        else:
            self._log("Bootstrapping frr.conf for RS {}...".format(rs_node.getName()))
            self._configure_frr_router(rs_node)

    def _configure_bird_router(self, rnode: Router):
        ifaces = ''
        has_localnet = False
        for iface in rnode.getInterfaces():
            net = iface.getNet()
            if net.isDirect():
                has_localnet = True
                ifaces += RoutingFileTemplates["rnode_bird_direct_interface"].format(
                    interfaceName = net.getName()
                )
        rnode.setFile("/etc/bird/bird.conf",
            RoutingFileTemplates["rnode_bird"].format(
              routerId = rnode.getLoopbackAddress()))
        rnode.appendStartCommand('[ ! -d /run/bird ] && mkdir /run/bird')
        rnode.appendStartCommand('bird -d', True)
        if has_localnet:
            rnode.addProtocol('direct', 'local_nets',
                              RoutingFileTemplates['rnode_bird_direct'].format(interfaces = ifaces))

    def _configure_frr_router(self, rnode: Router):
        rnode.setFile(
            "/frr_start",
            FrrFileTemplates["start_script"].format(
                pre_start="",
                daemons="".join(
                    FrrFileTemplates["start_daemon"].format(daemon=daemon)
                    for daemon in ["bgpd", "ospfd"]
                ),
            ),
        )
        self._ensure_frr_start_commands(rnode)

    def _ensure_frr_start_commands(self, rnode: Router):
        commands = [cmd for cmd, _ in rnode.getStartCommands()]
        if "chmod +x /frr_start" not in commands:
            rnode.appendStartCommand("chmod +x /frr_start")
        if "/frr_start" not in commands:
            rnode.appendStartCommand("/frr_start")

    def _render_bird_ospf(self, rnode: Router):
        intents = get_ospf_interface_intents(rnode)
        if not intents["active"] and not intents["passive"]:
            return

        timers = get_ospf_timers(rnode)
        ospf_interfaces = ''
        for name in intents["passive"]:
            ospf_interfaces += RoutingFileTemplates['bird_ospf_stub_interface'].format(interfaceName=name)
        for name in intents["active"]:
            ospf_interfaces += RoutingFileTemplates['bird_ospf_interface'].format(
                interfaceName=name,
                hello=timers["hello"],
                dead=timers["dead"],
            )

        if ospf_interfaces != '':
            rnode.addTable('t_ospf')
            rnode.addProtocol('ospf', 'ospf1', RoutingFileTemplates['bird_ospf_body'].format(
                interfaces=ospf_interfaces,
                tick=timers["tick"],
            ))
            rnode.addTablePipe('t_ospf')

    def _render_bird_control_plane(self, rnode: Router):
        sessions = get_bgp_sessions(rnode)
        self._render_bird_ospf(rnode)
        if sessions or has_bgp_connected_export(rnode):
            include_tables = not sessions or any(not session["route_server_client"] for session in sessions)
            ensure_bird_bgp_base(rnode, include_tables=include_tables)
        for session in sessions:
            rnode.addProtocol('bgp', session["render_name"], render_bird_protocol_body(session))

    def _render_frr_connected_export(self, router: Router) -> Tuple[str, bool]:
        prefixes: List[str] = []
        seen: Set[str] = set()
        for iface in router.getInterfaces():
            net = iface.getNet()
            if net.getType() == NetworkType.Bridge:
                continue
            if not net.isDirect():
                continue
            prefix = str(net.getPrefix())
            if iface.getAddress() is not None and prefix not in seen:
                seen.add(prefix)
                prefixes.append(prefix)

        body: List[str] = []
        for index, prefix in enumerate(prefixes, start=1):
            body.append(FrrFileTemplates["connected_prefix_list"].format(seq=index * 10, prefix=prefix))
        if prefixes:
            body.append(FrrFileTemplates["route_map_connected"].format(local_comm="{}:0:0".format(router.getAsn())))
        return "".join(body), bool(prefixes)

    def _render_frr_route_maps(self, local_asn: int, sessions: List[Dict]) -> Tuple[str, Dict[str, Dict[str, str]]]:
        body: List[str] = []
        map_names: Dict[str, Dict[str, str]] = {}
        for session in sessions:
            session_id = str(session.get("render_name") or session.get("name") or "session")
            import_name = ""
            import_community = str(session.get("import_community") or "").strip()
            local_pref = session.get("local_pref")
            if import_community and local_pref is not None:
                import_name = _frr_map_name("RM_IMPORT", session_id)
                body.append(
                    FrrFileTemplates["import_route_map"].format(
                        name=import_name,
                        community=render_frr_community(local_asn, import_community),
                        local_pref=int(local_pref),
                    )
                )

            export_name = _frr_map_name("RM_EXPORT", session_id)
            if session["export_policy"] == BGP_EXPORT_LOCAL_AND_CUSTOMER:
                body.append(FrrFileTemplates["export_route_map_local_customer"].format(name=export_name))
            else:
                body.append(FrrFileTemplates["export_route_map_all"].format(name=export_name))
            map_names[session_id] = {"import": import_name, "export": export_name}
        return "".join(body), map_names

    def _render_frr_bgp(self, router: Router) -> str:
        sessions = get_bgp_sessions(router)
        if not sessions and not has_bgp_connected_export(router):
            return ""

        body: List[str] = []
        body.append(
            FrrFileTemplates["community_lists"].format(
                local_comm="{}:0:0".format(router.getAsn()),
                customer_comm="{}:1:0".format(router.getAsn()),
            )
        )
        if has_bgp_connected_export(router):
            connected_body, has_connected = self._render_frr_connected_export(router)
        else:
            connected_body, has_connected = "", False
        body.append(connected_body)
        route_maps, map_names = self._render_frr_route_maps(router.getAsn(), sessions)
        body.append(route_maps)

        bgp: List[str] = [
            "router bgp {}".format(router.getAsn()),
            " bgp router-id {}".format(self._get_frr_router_id(router)),
            " no bgp ebgp-requires-policy",
            " no bgp default ipv4-unicast",
        ]
        rr_cluster_ids = {
            session["route_reflector_cluster_id"]
            for session in sessions
            if session["route_reflector_client"]
        }
        if len(rr_cluster_ids) > 1:
            raise ValueError(
                "FRR supports one route-reflector cluster-id per router, got {}".format(
                    ", ".join(sorted(rr_cluster_ids))
                )
            )
        if rr_cluster_ids:
            bgp.append(" bgp cluster-id {}".format(next(iter(rr_cluster_ids))))
        for session in sessions:
            bgp.append(" neighbor {} remote-as {}".format(session["peer_address"], session["peer_asn"]))
            bgp.append(" neighbor {} update-source {}".format(session["peer_address"], session["local_address"]))
            bgp.append(" neighbor {} description {}".format(session["peer_address"], session["name"]))
            bgp.append(
                " neighbor {} timers {} {}".format(
                    session["peer_address"],
                    session["keepalive_time"],
                    session["hold_time"],
                )
            )
            if session["passive"]:
                bgp.append(" neighbor {} passive".format(session["peer_address"]))
        bgp.append(" !")
        bgp.append(" address-family ipv4 unicast")
        if has_connected:
            bgp.append("  redistribute connected route-map RM_CONNECTED_TO_BGP")
        for session in sessions:
            session_id = str(session.get("render_name") or session.get("name") or "session")
            maps = map_names.get(session_id, {})
            bgp.append("  neighbor {} activate".format(session["peer_address"]))
            if session["next_hop_self"]:
                bgp.append("  neighbor {} next-hop-self".format(session["peer_address"]))
            if session["route_server_client"]:
                bgp.append("  neighbor {} route-server-client".format(session["peer_address"]))
            if session["route_reflector_client"]:
                bgp.append("  neighbor {} route-reflector-client".format(session["peer_address"]))
            if maps.get("import"):
                bgp.append("  neighbor {} route-map {} in".format(session["peer_address"], maps["import"]))
            if maps.get("export"):
                bgp.append("  neighbor {} route-map {} out".format(session["peer_address"], maps["export"]))
        bgp.append(" exit-address-family")
        bgp.append("!")
        body.append("\n".join(bgp) + "\n")
        return "".join(body)

    def _get_frr_router_id(self, router: Router) -> str:
        loopback = router.getLoopbackAddress()
        if loopback is not None:
            return str(loopback)
        ifaces = router.getInterfaces()
        assert len(ifaces) > 0, "router node {}/{} has no interfaces".format(router.getAsn(), router.getName())
        return str(ifaces[0].getAddress())

    def _render_frr_ospf(self, router: Router) -> str:
        intents = get_ospf_interface_intents(router)
        if not intents["active"] and not intents["passive"]:
            return ""

        timers = get_ospf_timers(router)
        body: List[str] = []
        for name in intents["passive"]:
            body.append(FrrFileTemplates["ospf_interface_passive"].format(interface=name))
        for name in intents["active"]:
            body.append(
                FrrFileTemplates["ospf_interface_active"].format(
                    interface=name,
                    hello=timers["hello"],
                    dead=timers["dead"],
                )
            )
        body.append(FrrFileTemplates["ospf_router"].format(router_id=router.getLoopbackAddress()))
        return "".join(body)

    def _render_frr_mpls(self, router: Router) -> Tuple[str, List[str], int]:
        intent = get_mpls_ldp_intent(router)
        interfaces = intent["interfaces"]
        if not interfaces:
            return "", [], int(intent["platform_labels"])

        ospf_interfaces = "".join(
            FrrFileTemplates["mpls_ospf_interface"].format(interface=interface)
            for interface in interfaces
        )
        ldp_interfaces = "".join(
            FrrFileTemplates["mpls_ldp_interface"].format(interface=interface)
            for interface in interfaces
        )
        return (
            FrrFileTemplates["mpls_config"].format(
                router_id=router.getLoopbackAddress(),
                ospf_interfaces=ospf_interfaces,
                ldp_interfaces=ldp_interfaces,
            ),
            interfaces,
            int(intent["platform_labels"]),
        )

    def _render_frr_start_script(
        self,
        *,
        bgp: bool,
        ospf: bool,
        mpls_interfaces: List[str],
        platform_labels: int,
    ) -> str:
        daemons: List[str] = []
        if bgp:
            daemons.append("bgpd")
        if ospf or mpls_interfaces:
            daemons.append("ospfd")
        if mpls_interfaces:
            daemons.append("ldpd")
        return FrrFileTemplates["start_script"].format(
            pre_start=(
                FrrFileTemplates["mpls_start"].format(platform_labels=platform_labels)
                if mpls_interfaces
                else ""
            ),
            daemons="".join(
                FrrFileTemplates["start_daemon"].format(daemon=daemon)
                for daemon in daemons
            ),
        )

    def _render_frr_control_plane(self, router: Router, *, include_ospf: bool = True, include_bgp: bool = True):
        ospf_body = self._render_frr_ospf(router) if include_ospf else ""
        bgp_body = self._render_frr_bgp(router) if include_bgp else ""
        mpls_body, mpls_interfaces, platform_labels = self._render_frr_mpls(router)
        body = ospf_body + bgp_body + mpls_body
        router.setFile(
            "/etc/frr/frr.conf",
            FrrFileTemplates["managed_block"].format(
                hostname="as{}_{}".format(router.getAsn(), router.getName()),
                body=body,
            ),
        )
        router.setFile(
            "/frr_start",
            self._render_frr_start_script(
                bgp=bool(bgp_body),
                ospf=bool(ospf_body),
                mpls_interfaces=mpls_interfaces,
                platform_labels=platform_labels,
            ),
        )
        self._ensure_frr_start_commands(router)
        if mpls_interfaces:
            router.setFile("/mpls_ifaces.txt", "\n".join(mpls_interfaces))

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        reg = emulator.getRegistry()
        for ((scope, type, name), obj) in reg.getAll().items():
            if type == 'rs':
                rs_node: Node = obj
                backend = get_bgp_backend(rs_node)
                if backend == BGP_BACKEND_BIRD:
                    self._installBird(rs_node)
                else:
                    self._installFrr(rs_node)
                self._configure_rs(rs_node)
            if type == 'rnode':
                rnode: Router = obj
                assert issubclass(rnode.__class__, Router)

                self._log("Setting up loopback interface for AS{} Router {}...".format(scope, name))

                if rnode.getLoopbackAddress() == None:
                    lbaddr = self._loopback_assigner[self._loopback_pos]
                else:
                    lbaddr = rnode.getLoopbackAddress()

                rnode.appendStartCommand('ip li add dummy0 type dummy')
                rnode.appendStartCommand('ip li set dummy0 up')
                rnode.appendStartCommand('ip addr add {}/32 dev dummy0'.format(lbaddr))
                rnode.setLabel('loopback_addr', lbaddr)
                rnode.setLoopbackAddress(lbaddr)
                self._loopback_pos += 1

                backend = get_bgp_backend(rnode)
                self._log("Bootstrapping {} routing config for AS{} Router {}...".format(backend, scope, name))

                if backend == BGP_BACKEND_BIRD:
                    self._installBird(rnode)
                else:
                    self._installFrr(rnode)

                r_ifaces = rnode.getInterfaces()
                assert len(r_ifaces) > 0, "router node {}/{} has no interfaces".format(rnode.getAsn(), rnode.getName())

                if backend == BGP_BACKEND_BIRD:
                    self._configure_bird_router(rnode)
                else:
                    self._configure_frr_router(rnode)

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
                if backend == BGP_BACKEND_BIRD:
                    self._render_bird_control_plane(rs_node)
                else:
                    self._render_frr_control_plane(rs_node)

            if type == 'rnode':
                rnode: Router = obj
                backend = get_bgp_backend(rnode)
                if backend == BGP_BACKEND_BIRD:
                    assert not get_mpls_ldp_intent(rnode)["interfaces"], (
                        "MPLS requires FRR routing backend; AS{}/{} uses bird. "
                        "BIRD does not support MPLS/LDP in this emulator path."
                    ).format(rnode.getAsn(), rnode.getName())
                    self._render_bird_control_plane(rnode)
                else:
                    self._render_frr_control_plane(rnode)

                if rnode.hasExtension('RealWorldRouter'): # could also be ScionRouter which needs RealWorldAccess

                    # this is an exception - Only for service net (not part of simulation)
                    rnode._Node__joinNetwork(svc_net)
                    [l, b, d] = svc_net.getDefaultLinkProperties()
                    rnode.appendFile('/ifinfo.txt',
                                     '{}:{}:{}:{}:{}\n'.format(svc_net.getName(), svc_net.getPrefix(), l, b, d))

                    self._log("Sealing real-world router as{}/{}...".format(rnode.getAsn(), rnode.getName()))
                    rnode.seal(svc_net)

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

                if rif == None and hnet.getType() != NetworkType.Local:
                    services = hnode.getAttribute('services', {}) or {}
                    if "ExaBgpService" in services:
                        self._log("Skipping default route for ExaBGP speaker {} in as{} on non-local network {}.".format(
                            name, scope, hnet.getName()
                        ))
                        continue

                assert rif != None, 'Host {} in as{} in network {}: no router'.format(name, scope, hnet.getName())
                self._log("Setting default route for host {} ({}) to router {}".format(name, hif.getAddress(), rif.getAddress()))
                hnode.appendStartCommand('ip rou del default 2> /dev/null')
                hnode.appendStartCommand('ip route add default via {} dev {}'.format(rif.getAddress(), rif.getNet().getName()))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RoutingLayer: BIRD 2.0.x / FRRouting\n'

        return out
