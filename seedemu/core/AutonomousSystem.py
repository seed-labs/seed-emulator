from __future__ import annotations
from .Graphable import Graphable
from .Printable import Printable
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .enums import NetworkType, NodeRole
from .Node import Node, Router
from .Scope import ScopeTier, Scope
from .Emulator import Emulator
from .Configurable import Configurable
from .Customizable import Customizable
from .Node import promote_to_real_world_router
from ipaddress import IPv4Network
from typing import Dict, List, Tuple, Set
import requests

RIS_PREFIXLIST_URL = 'https://stat.ripe.net/data/announced-prefixes/data.json'

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
    __clusters: Dict[str, Tuple[Set[str], Set[str]]] # cluster_id -> (set of rr names, set of client names)

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

    def createCluster(self, address: str) -> 'AutonomousSystem':
        """
        显式注册一个 Cluster ID。
        如果该 ID 已存在，则不做任何事；如果不存在，初始化为空集合。
        """
        if address not in self.__clusters:
            # 初始化两个空的 Set：一个存 RR，一个存 Client
            self.__clusters[address] = (set(), set())
            
        return self
    def _validate_cluster_integrity(self, data: Dict[str, Tuple[Set[str], Set[str]]]):
        """
        [修改后的校验逻辑]
        规则更新：
        1. 如果全网只有一个“活跃” Cluster，且该 Cluster 内没有 RR：
           -> 判定为传统 Full Mesh 模式，合法，跳过检查。
        2. 如果全网有多个 Cluster，或者只有一个 Cluster 但存在 RR：
           -> 判定为 RR 模式，必须严格检查：
              a. 每个 Cluster 必须有 RR（用于跨 Cluster 互联）。
              b. 每个 Cluster 如果有 RR，必须有 Client（否则 RR 没有存在的意义）。
        """

        # 1. 特殊情况豁免：单 Cluster 且无 RR -> Full Mesh 模式
        if len(data) == 1:
            # 获取唯一的那个 Cluster 的数据
            cid, (rrs, clients) = list(data.items())[0]
            
            # 如果没有 RR，说明这是纯 Client（Peer）集合，走 Full Mesh，合法！
            if len(rrs) == 0:
                return 
        
        # 2. 常规严格检查 (适用于多 Cluster 场景，或单 Cluster RR 场景)
        for cid, (rr_set, client_set) in data.items():
            
            # 规则 A: 必须有 RR
            # (在多 Cluster 架构中，没有 RR 的 Cluster 无法与其他 Cluster 通信)
            assert len(rr_set) > 0, (
                f"[Topology Error] AS{self.__asn} Cluster '{cid}' is invalid: "
                f"Missing Route Reflector! In a multi-cluster or RR topology, every cluster must have an RR."
            )
            
            # 规则 B: 如果有 RR，必须有 Client
            # (响应你之前的需求：有 RR 没 Client 要报错)
            assert len(client_set) > 0, (
                f"[Topology Error] AS{self.__asn} Cluster '{cid}' is invalid: "
                f"Missing Clients! The Route Reflector {list(rr_set)} has no clients to serve."
            )

    def _aggregateBgpClusters(self):
        """
        聚合逻辑：
        1. 获取显式定义的 clusters。
        2. 遍历所有 Router，读取它们身上的配置。
        3. 如果 Router 指定了 cluster_id，归入该 Cluster。
        4. 如果 Router 没指定，归入缺省 Cluster (Default Cluster)。
        """
        # 步骤 A: 建立一个临时字典用于合并数据
        # 这里先复制一份已有的显式配置
        merged_data = self.__clusters.copy()

        # 辅助函数：确保 key 存在
        def ensure_key(cid):
            assert cid in merged_data, f"Cluster ID {cid} doesn't exists in Cluster!"

        # 步骤 B: 生成缺省 Cluster ID (例如 0.0.0.0)
        default_cluster_id = "10.0.0.0"


        # 步骤 C: 遍历所有 Router，通过 Router 自身状态进行归类
        for router in self.__routers.values():
            # 获取 Router 自身的设置
            # 假设 Router 类有 getBgpClusterId() 和 isRouteReflector()
            r_cid = router.getBgpClusterId()
            is_rr = router.isRouteReflector()
            r_name = router.getName()

            # 逻辑判定：
            # 1. 如果 Router 设置了 cluster_id，就用它的。
            # 2. 如果没设置，就归入缺省 Cluster。
            if r_cid is not None:
                ensure_key(r_cid)
                target_cid = r_cid
            else:
                if default_cluster_id not in merged_data:
                    # 初始化缺省 Cluster
                    merged_data[default_cluster_id] = (set(), set())    
                target_cid = default_cluster_id

            # 加入对应的集合
            if is_rr:
                merged_data[target_cid][0].add(r_name)
            else:
                merged_data[target_cid][1].add(r_name)
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

    def createRouter(self, name: str) -> Node:
        """!
        @brief Create a router node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__routers, 'Router with name {} already exists.'.format(name)
        self.__routers[name] = Router(name, NodeRole.Router, self.__asn)

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