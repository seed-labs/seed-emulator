from __future__ import annotations
from .Graphable import Graphable
from .Printable import Printable
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .enums import NetworkType, NodeRole
from .Node import Node, Router, ROUTER_BGP_ROLE_EDGE
from .Scope import ScopeTier, Scope
from .Emulator import Emulator
from .Configurable import Configurable
from .Customizable import Customizable
from .Node import promote_to_real_world_router
from ipaddress import IPv4Network
from typing import Dict, List, Optional, Set, Tuple
import requests

RIS_PREFIXLIST_URL = 'https://stat.ripe.net/data/announced-prefixes/data.json'

IBGP_MODE_FULL_MESH = "full-mesh"
IBGP_MODE_ROUTE_REFLECTOR = "route-reflector"
IBGP_MODE_DISABLED = "disabled"

IBGP_MODES = {
    IBGP_MODE_FULL_MESH,
    IBGP_MODE_ROUTE_REFLECTOR,
    IBGP_MODE_DISABLED,
}

BGP_SCOPE_ALL_ROUTERS = "all-routers"
BGP_SCOPE_EDGE_ONLY = "edge-only"
BGP_SCOPES = {BGP_SCOPE_ALL_ROUTERS, BGP_SCOPE_EDGE_ONLY}

CORE_FORWARDING_PLAIN_IP = "plain-ip"
CORE_FORWARDING_MPLS = "mpls"
CORE_FORWARDING_SR = "sr"
CORE_FORWARDING_TUNNEL = "tunnel"
CORE_FORWARDING_REDISTRIBUTE = "redistribute"
CORE_FORWARDING_MODES = {
    CORE_FORWARDING_PLAIN_IP,
    CORE_FORWARDING_MPLS,
    CORE_FORWARDING_SR,
    CORE_FORWARDING_TUNNEL,
    CORE_FORWARDING_REDISTRIBUTE,
}

OSPF_MODE_LEGACY = "legacy"
OSPF_MODE_ROUTER_TRANSIT_ONLY = "router-transit-only"
OSPF_MODES = {OSPF_MODE_LEGACY, OSPF_MODE_ROUTER_TRANSIT_ONLY}

class AutonomousSystem(Printable, Graphable, Configurable, Customizable):
    """!
    @brief AutonomousSystem class.

    This class represents an autonomous system.
    """

    __asn: int
    __subnets: List[IPv4Network]
    __routers: Dict[str, Node]
    __hosts: Dict[str, Node]
    __nets: Dict[str, Network]
    __name_servers: List[str]
    __clusters: Dict[str, Tuple[Set[str], Set[str]]]
    __ibgp_mode: str
    __ibgp_mode_explicit: bool
    __bgp_scope: str
    __core_forwarding: str
    __ospf_mode: str
    __ospf_mode_explicit: bool

    def __init__(self, asn: int, subnetTemplate: str = "10.{}.0.0/16"):
        """!
        @brief AutonomousSystem constructor.

        @param asn ASN for this system.
        @param subnetTemplate (optional) template for assigning subnet.
        """
        super().__init__()
        self.__hosts = {}
        self.__routers = {}
        self.__nets = {}
        self.__asn = asn
        self.__subnets = None if asn > 255 else list(IPv4Network(subnetTemplate.format(asn)).subnets(new_prefix = 24))
        self.__name_servers = []
        self.__clusters = {}
        self.__ibgp_mode = IBGP_MODE_FULL_MESH
        self.__ibgp_mode_explicit = False
        self.__bgp_scope = BGP_SCOPE_ALL_ROUTERS
        self.__core_forwarding = CORE_FORWARDING_PLAIN_IP
        self.__ospf_mode = OSPF_MODE_LEGACY
        self.__ospf_mode_explicit = False

    def setIbgpMode(self, mode: str) -> AutonomousSystem:
        """!
        @brief Set the AS-level iBGP route propagation mode.

        The default is full-mesh when unset. This setting records AS
        intent; the Ibgp layer still renders concrete BGP sessions.

        @param mode full-mesh, route-reflector, or disabled.

        @returns self, for chaining API calls.
        """
        value = self._normalizeIbgpMode(mode)
        assert value in IBGP_MODES, "unsupported iBGP mode: {}. valid values: {}".format(
            mode, sorted(IBGP_MODES)
        )
        self.__ibgp_mode = value
        self.__ibgp_mode_explicit = True
        return self

    def _normalizeIbgpMode(self, mode: str) -> str:
        value = str(mode or IBGP_MODE_FULL_MESH).strip().lower()
        return value

    def getIbgpMode(self) -> str:
        """!
        @brief Get the AS-level iBGP route propagation mode.
        """
        return self.__ibgp_mode

    def hasIbgpMode(self) -> bool:
        """!
        @brief Return whether an iBGP mode was explicitly set on this AS.
        """
        return self.__ibgp_mode_explicit

    def setBgpScope(self, scope: str) -> AutonomousSystem:
        """!
        @brief Set which routers participate in BGP/iBGP inside this AS.

        @param scope all-routers or edge-only.

        @returns self, for chaining API calls.
        """
        value = str(scope or BGP_SCOPE_ALL_ROUTERS).strip().lower()
        assert value in BGP_SCOPES, "unsupported BGP scope: {}. valid values: {}".format(
            scope, sorted(BGP_SCOPES)
        )
        self.__bgp_scope = value
        return self

    def getBgpScope(self) -> str:
        """!
        @brief Get the AS-level BGP participation scope.
        """
        return self.__bgp_scope

    def setCoreForwarding(self, mode: str) -> AutonomousSystem:
        """!
        @brief Set the forwarding mechanism expected for a BGP-free core.

        @param mode plain-ip, mpls, sr, tunnel, or redistribute.

        @returns self, for chaining API calls.
        """
        value = str(mode or CORE_FORWARDING_PLAIN_IP).strip().lower()
        assert value in CORE_FORWARDING_MODES, "unsupported core forwarding mode: {}. valid values: {}".format(
            mode, sorted(CORE_FORWARDING_MODES)
        )
        self.__core_forwarding = value
        return self

    def getCoreForwarding(self) -> str:
        """!
        @brief Get the AS-level core forwarding mode.
        """
        return self.__core_forwarding

    def setIbgpDesign(
        self,
        mode: str = IBGP_MODE_FULL_MESH,
        scope: str = BGP_SCOPE_ALL_ROUTERS,
        core_forwarding: str = CORE_FORWARDING_PLAIN_IP,
    ) -> AutonomousSystem:
        """!
        @brief Set iBGP mode, BGP scope, and core forwarding together.
        """
        self.setIbgpMode(mode)
        self.setBgpScope(scope)
        self.setCoreForwarding(core_forwarding)
        return self

    def setOspfMode(self, mode: str) -> AutonomousSystem:
        """!
        @brief Set the AS-level OSPF interface classification mode.

        The default is legacy when unset. Ospf records interface intent and
        Routing renders backend-specific BIRD/FRR configuration.

        @param mode legacy or router-transit-only.

        @returns self, for chaining API calls.
        """
        value = str(mode or OSPF_MODE_LEGACY).strip().lower()
        assert value in OSPF_MODES, "unsupported OSPF mode: {}".format(mode)
        self.__ospf_mode = value
        self.__ospf_mode_explicit = True
        return self

    def getOspfMode(self) -> str:
        """!
        @brief Get the AS-level OSPF interface classification mode.
        """
        return self.__ospf_mode

    def hasOspfMode(self) -> bool:
        """!
        @brief Return whether an OSPF mode was explicitly set on this AS.
        """
        return self.__ospf_mode_explicit

    def createBgpCluster(self, address: str) -> AutonomousSystem:
        """!
        @brief Register an iBGP Route Reflector cluster ID for this AS.

        The cluster starts with empty RR/client membership. Calling this method
        with an existing cluster ID is idempotent.

        @param address cluster ID rendered into BIRD's rr cluster id field.

        @returns self, for chaining API calls.
        """
        self.__ensureRouteReflectorModeAllowed("createBgpCluster")
        if not self.__ibgp_mode_explicit:
            self.__ibgp_mode = IBGP_MODE_ROUTE_REFLECTOR
            self.__ibgp_mode_explicit = True
        if address not in self.__clusters:
            self.__clusters[address] = (set(), set())

        return self

    def __ensureRouteReflectorModeAllowed(self, api_name: str) -> None:
        if self.__ibgp_mode_explicit and self.__ibgp_mode != IBGP_MODE_ROUTE_REFLECTOR:
            raise AssertionError(
                "AS{} cannot call {} while ibgp_mode is {}".format(
                    self.__asn, api_name, self.__ibgp_mode
                )
            )

    def __hasRouteReflectorRouterConfig(self) -> bool:
        for router in self.__routers.values():
            if router.getBgpClusterId() is not None or router.isRouteReflector():
                return True
        return False

    def __hasRouteReflectorConfig(self) -> bool:
        return len(self.__clusters) > 0 or self.__hasRouteReflectorRouterConfig()

    def __defaultBgpClusterId(self) -> str:
        if self.__asn <= 255:
            base = "10.{}.0".format(self.__asn)
        else:
            base = "10.{}.{}".format((self.__asn // 256) % 256, self.__asn % 256)

        for suffix in range(1, 255):
            candidate = "{}.{}".format(base, suffix)
            if candidate not in self.__clusters:
                return candidate

        raise AssertionError("AS{} cannot allocate a default BGP cluster ID".format(self.__asn))

    def __getIbgpParticipantRouters(self) -> List[Router]:
        routers = list(self.__routers.values())
        if self.__bgp_scope == BGP_SCOPE_ALL_ROUTERS:
            return routers

        participants = [
            router for router in routers
            if (
                (hasattr(router, "getBgpRole") and router.getBgpRole() == ROUTER_BGP_ROLE_EDGE)
                or router.isBorderRouter()
            )
        ]
        assert len(participants) > 0, (
            "AS{} has bgp_scope=edge-only but no edge routers were found; "
            "mark routers with setBgpRole('edge') or connect them to IXes".format(self.__asn)
        )
        return participants

    def getIbgpParticipants(self) -> Set[str]:
        """!
        @brief Get router names participating in the AS iBGP design.
        """
        return {router.getName() for router in self.__getIbgpParticipantRouters()}

    def _validate_cluster_integrity(self, data: Dict[str, Tuple[Set[str], Set[str]]]):
        """!
        @brief Validate Route Reflector cluster membership.

        @param data mapping from cluster ID to RR names and client names.
        """
        for cid, (rr_set, client_set) in data.items():
            assert len(rr_set) > 0, (
                "[Topology Error] AS{} cluster '{}' is invalid: missing Route "
                "Reflector.".format(self.__asn, cid)
            )
            assert len(client_set) > 0, (
                "[Topology Error] AS{} cluster '{}' is invalid: missing clients. "
                "Route Reflector(s) {} have no clients to serve.".format(
                    self.__asn, cid, sorted(rr_set)
                )
            )

    def completeIbgpSetup(self) -> AutonomousSystem:
        """!
        @brief Complete and validate the AS-level iBGP design.

        The AS owns iBGP intent. The Ibgp layer only renders the completed
        design into router configuration.
        """
        mode = self.getIbgpMode()
        has_rr_config = self.__hasRouteReflectorConfig()

        if mode == IBGP_MODE_FULL_MESH:
            if self.hasIbgpMode() and has_rr_config:
                raise AssertionError(
                    "AS{} has route-reflector cluster/router configuration but ibgp_mode is full-mesh".format(
                        self.__asn
                    )
                )
            if not self.hasIbgpMode() and has_rr_config:
                self.__ibgp_mode = IBGP_MODE_ROUTE_REFLECTOR
                mode = IBGP_MODE_ROUTE_REFLECTOR

        if mode == IBGP_MODE_DISABLED:
            return self

        participants = self.__getIbgpParticipantRouters()
        if mode == IBGP_MODE_FULL_MESH:
            return self

        assert mode == IBGP_MODE_ROUTE_REFLECTOR, "unsupported iBGP mode: {}".format(mode)

        explicit_clusters = len(self.__clusters) > 0
        advanced_multi_cluster = len(self.__clusters) > 1

        if not explicit_clusters:
            self.createBgpCluster(self.__defaultBgpClusterId())

        if advanced_multi_cluster:
            self.__completeAdvancedRouteReflectorSetup(participants)
        else:
            self.__completeDefaultRouteReflectorSetup(participants)

        return self

    def __completeDefaultRouteReflectorSetup(self, participants: List[Router]) -> None:
        assert len(participants) > 0, "AS{} route-reflector mode requires at least one router".format(self.__asn)
        cluster_id = sorted(self.__clusters.keys())[0]

        for router in participants:
            if router.getBgpClusterId() is None:
                router.joinBgpCluster(cluster_id)
            assert router.getBgpClusterId() == cluster_id, (
                "AS{} router {} joined unknown or non-default cluster {}".format(
                    self.__asn, router.getName(), router.getBgpClusterId()
                )
            )

        rrs = [router for router in participants if router.isRouteReflector()]
        if not rrs:
            sorted(participants, key=lambda router: router.getName())[0].makeRouteReflector()

        self._aggregateBgpClusters(validate=True)

    def __completeAdvancedRouteReflectorSetup(self, participants: List[Router]) -> None:
        cluster_ids = set(self.__clusters.keys())
        participant_names = {router.getName() for router in participants}

        for router in participants:
            cluster_id = router.getBgpClusterId()
            assert cluster_id is not None, (
                "Router {} in AS{} is missing a cluster ID".format(router.getName(), self.__asn)
            )
            assert cluster_id in cluster_ids, (
                "Router {} in AS{} joined unknown cluster {}".format(
                    router.getName(), self.__asn, cluster_id
                )
            )

        data = self._aggregateBgpClusters(validate=False)
        data = {
            cid: (rrs & participant_names, clients & participant_names)
            for cid, (rrs, clients) in data.items()
        }
        self._validate_cluster_integrity(data)
        self.__clusters = data

    def _aggregateBgpClusters(self, validate: bool = True) -> Dict[str, Tuple[Set[str], Set[str]]]:
        """!
        @brief Build Route Reflector cluster membership from AS/router state.

        Explicitly registered clusters provide the allowed cluster IDs. Routers
        that joined a cluster are assigned to that cluster; routers without an
        explicit cluster are assigned to the implicit default cluster.

        @returns mapping from cluster ID to RR names and client names.
        """
        merged_data = {
            cid: (set(rrs), set(clients))
            for cid, (rrs, clients) in self.__clusters.items()
        }

        for router in self.__getIbgpParticipantRouters():
            r_cid = router.getBgpClusterId()
            is_rr = router.isRouteReflector()
            r_name = router.getName()

            if r_cid is not None:
                assert r_cid in merged_data, "Cluster ID {} does not exist in AS{}.".format(
                    r_cid, self.__asn
                )
                target_cid = r_cid
            else:
                assert len(merged_data) == 1, (
                    "Router {} in AS{} is missing a cluster ID".format(r_name, self.__asn)
                )
                target_cid = next(iter(merged_data.keys()))

            if is_rr:
                merged_data[target_cid][0].add(r_name)
            else:
                merged_data[target_cid][1].add(r_name)

        if validate:
            self._validate_cluster_integrity(merged_data)
        self.__clusters = merged_data
        return self.__clusters


    def setNameServers(self, servers: List[str]) -> AutonomousSystem:
        """!
        @brief set recursive name servers to use on nodes in this AS. Overwrites
        emulator-level settings.

        @param servers list of IP addresses of recursive name servers. Set to
        empty list to use default (i.e., do not change, or use emulator-level
        settings)

        @returns self, for chaining API calls.
        """
        self.__name_servers = servers

        return self

    def getNameServers(self) -> List[str]:
        """!
        @brief get configured recursive name servers for nodes in this AS.

        @returns list of IP addresses of recursive name servers
        """
        return self.__name_servers

    def getPrefixList(self) -> List[str]:
        """!
        @brief Helper tool, get real-world prefix list for the current ans by
        RIPE RIS.

        @throw AssertionError if API failed.
        """

        rslt = requests.get(RIS_PREFIXLIST_URL, {
            'resource': self.__asn
        })

        assert rslt.status_code == 200, 'RIPEstat API returned non-200'

        json = rslt.json()
        assert json['status'] == 'ok', 'RIPEstat API returned not-OK'

        return [p['prefix'] for p in json['data']['prefixes'] if ':' not in p['prefix']]

    def registerNodes(self, emulator: Emulator):
        """!
        @brief register all nodes in the as in the emulation.

        Note: this is to be invoked by the renderer.

        @param emulator emulator to register nodes in.
        """

        reg = emulator.getRegistry()

        for val in list(self.__nets.values()):
            net: Network = val
            # Rap creates a new node for the provider and thus has to be set up
            # before node registration
            if net.getRemoteAccessProvider() != None:
                rap = net.getRemoteAccessProvider()

                brNode = self.createOpenVpnRouter('br-{}'.format(net.getName()))
                brNet = emulator.getServiceNetwork()

                rap.configureRemoteAccess(emulator, net, brNode, brNet)
            # .. whereas RealWorldConnectivity doesn't, so it can be moved to a later point
            #  (after the services[which might require real-world-access] have been configured)
            #if (p:=net.getExternalConnectivityProvider()) != None:
            #    p.configureExternalLink(emulator, net, localNet of brNode , emulator.getServiceNet() )

        if any([r.hasExtension('RealWorldRouter') for r in list(self.__routers.values())]):
            _ = emulator.getServiceNetwork() # this will construct and register Svc Net with registry

        for (key, val) in self.__nets.items(): reg.register(str(self.__asn), 'net', key, val)
        for (key, val) in self.__hosts.items(): reg.register(str(self.__asn), 'hnode', key, val)
        for (key, val) in self.__routers.items(): reg.register(str(self.__asn), 'rnode', key, val)

    def inheritOptions(self, emulator: Emulator):
        """! trickle down any overrides the user might have done on AS level """
        # since global defaults are set on node level rather than AS level by the DynamicConfigurable impl
        # this causes no redundant setting of the same options/defaults
        reg = emulator.getRegistry()
        all_nodes = [ obj for (scope,typ,name),obj  in reg.getAll( ).items()
                      if scope==str(self.getAsn()) and typ in ['rnode','hnode','csnode','rsnode','rs'] ]
        for n in all_nodes:
            self.handDown(n)

    def scope(self)-> Scope:
        """return a scope specific to this AS"""
        return Scope(ScopeTier.AS, as_id=self.getAsn())


    def configure(self, emulator: Emulator):
        """!
        @brief configure all nodes in the as in the emulation.

        Note: this is to be invoked by the renderer.

        @param emulator emulator to configure nodes in.
        """
        for host in self.__hosts.values():
            if len(host.getNameServers()) == 0:
                host.setNameServers(self.__name_servers)

            host.configure(emulator)

        for name, router in self.__routers.items():
            if len(router.getNameServers()) == 0:
                router.setNameServers(self.__name_servers)

            router.configure(emulator)
            if router.isBorderRouter():
                emulator.getRegistry().register( str(self.__asn), 'brdnode', name, router )

    def getAsn(self) -> int:
        """!
        @brief Get ASN.

        @returns asn.
        """
        return self.__asn

    def createNetwork(self, name: str, prefix: str = "auto", direct: bool = True, aac: AddressAssignmentConstraint = None) -> Network:
        """!
        @brief Create a new network.

        @param name name of the new network.
        @param prefix optional. Network prefix of this network. If not set, a
        /24 subnet of "10.{asn}.{id}.0/24" will be used, where asn is ASN of
        this AS, and id is a self-incremental value starts from 0.
        @param direct optional. direct flag of the network. A direct network
        will be added to RIB of routing daemons. Default to true.
        @param aac optional. AddressAssignmentConstraint to use. Default to
        None.

        @returns Network.
        @throws StopIteration if subnet exhausted.
        """
        assert prefix != "auto" or self.__asn <= 255, "can't use auto: asn > 255"

        network = IPv4Network(prefix) if prefix != "auto" else self.__subnets.pop(0)
        assert name not in self.__nets, 'Network with name {} already exist.'.format(name)
        self.__nets[name] = Network(name, NetworkType.Local, network, aac, direct)

        return self.__nets[name]

    def getNetwork(self, name: str) -> Network:
        """!
        @brief Retrieve a network.

        @param name name of the network.
        @returns Network.
        """
        return self.__nets[name]

    def getNetworks(self) -> List[str]:
        """!
        @brief Get list of name of networks.

        @returns list of networks.
        """
        return list(self.__nets.keys())

    def createRouter(self, name: str, routingBackend: str = "bird") -> Node:
        """!
        @brief Create a router node.

        @param name name of the new node.
        @param routingBackend routing daemon backend, bird or frr. Default to bird.
        @returns Node.
        """
        assert name not in self.__routers, 'Router with name {} already exists.'.format(name)
        self.__routers[name] = Router(name, NodeRole.Router, self.__asn, routingBackend=routingBackend)

        return self.__routers[name]

    def createRealWorldRouter(self, name: str, hideHops: bool = True, prefixes: List[str] = None) -> Node:
        """!
        @brief Create a real-world router node.

        A real-world router nodes are connect to a special service network,
        and can route traffic from the emulation to the real world.

        @param name name of the new node.
        @param hideHops (optional) hide real world hops from traceroute (by
        setting TTL = 64 to all real world dists on POSTROUTING). Default to
        True.
        @param prefixes (optional) prefixes to announce. If unset, will try to
        get prefixes from real-world DFZ via RIPE RIS. Default to None (get from
        RIS)
        @returns new node.
        """
        assert name not in self.__routers, 'Router with name {} already exists.'.format(name)

        router = Router(name, NodeRole.Router, self.__asn)
        router = promote_to_real_world_router(router, hideHops)

        if prefixes == None:
            prefixes = self.getPrefixList()

        for prefix in prefixes:
            router.addRealWorldRoute(prefix)

        self.__routers[name] = router

        return router

    def getRouters(self) -> List[str]:
        """!
        @brief Get list of name of routers.

        @returns list of routers.
        """
        return list(self.__routers.keys())

    def getBorderRouters(self)->List[str]:
        """
        @brief return the subset of all routers that participate in inter-domain routing
        """
        return [router for name, router in self.__routers.items() if router.isBorderRouter() ]

    def getRouter(self, name: str) -> Node:
        """!
        @brief Retrieve a router node.

        @param name name of the node.
        @returns Node.
        """
        return self.__routers[name]

    def createHost(self, name: str) -> Node:
        """!
        @brief Create a host node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__hosts, 'Host with name {} already exists.'.format(name)
        self.__hosts[name] = Node(name, NodeRole.Host, self.__asn)

        return self.__hosts[name]

    def getHost(self, name: str) -> Node:
        """!
        @brief Retrieve a host node.

        @param name name of the node.
        @returns Node.
        """
        return self.__hosts[name]

    def getHosts(self) -> List[str]:
        """!
        @brief Get list of name of hosts.

        @returns list of hosts.
        """
        return list(self.__hosts.keys())

    def _doCreateGraphs(self, emulator: Emulator):
        """!
        @brief create l2 connection graphs.
        """

        l2graph = self._addGraph('AS{}: Layer 2 Connections'.format(self.__asn), False)

        for obj in self.__nets.values():
            net: Network = obj
            l2graph.addVertex('Network: {}'.format(net.getName()), shape = 'rectangle', group = 'AS{}'.format(self.__asn))

        for obj in self.__routers.values():
            router: Node = obj
            rtrname = 'Router: {}'.format(router.getName(), group = 'AS{}'.format(self.__asn))
            l2graph.addVertex(rtrname, group = 'AS{}'.format(self.__asn), shape = 'diamond')
            for iface in router.getInterfaces():
                net = iface.getNet()
                netname = 'Network: {}'.format(net.getName())
                if net.getType() == NetworkType.InternetExchange:
                    netname = 'Exchange: {}...'.format(net.getName())
                    l2graph.addVertex(netname, shape = 'rectangle')
                if net.getType() == NetworkType.CrossConnect:
                    netname = 'CrossConnect: {}...'.format(net.getName())
                    l2graph.addVertex(netname, shape = 'rectangle')
                l2graph.addEdge(rtrname, netname)

        for obj in self.__hosts.values():
            router: Node = obj
            rtrname = 'Host: {}'.format(router.getName(), group = 'AS{}'.format(self.__asn))
            l2graph.addVertex(rtrname, group = 'AS{}'.format(self.__asn))
            for iface in router.getInterfaces():
                net = iface.getNet()
                netname = 'Network: {}'.format(net.getName())
                l2graph.addEdge(rtrname, netname)

        # todo: better xc graphs?

    def print(self, indent: int) -> str:
        """!
        @brief print AS details (nets, hosts, routers).

        @param indent indent.

        @returns printable string.
        """

        out = ' ' * indent
        out += 'AutonomousSystem {}:\n'.format(self.__asn)

        indent += 4
        out += ' ' * indent
        out += 'Networks:\n'

        for net in self.__nets.values():
            out += net.print(indent + 4)

        out += ' ' * indent
        out += 'Routers:\n'

        for node in self.__routers.values():
            out += node.print(indent + 4)

        out += ' ' * indent
        out += 'Hosts:\n'

        for host in self.__hosts.values():
            out += host.print(indent + 4)

        return out

    def createOpenVpnRouter(self, name: str) -> Node:
        """!
        @brief Create a OpenVpn router node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__routers, 'Router with name {} already exists.'.format(name)
        self.__routers[name] = Router(name, NodeRole.OpenVpnRouter, self.__asn)

        return self.__routers[name]
