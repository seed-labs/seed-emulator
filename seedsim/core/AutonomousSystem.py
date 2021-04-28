from .Graphable import Graphable
from .Printable import Printable
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .Registry import ScopedRegistry
from .enums import NetworkType, NodeRole
from .Node import Node
from .Simulator import Simulator
from .Configurable import Configurable
from ipaddress import IPv4Network
from typing import Dict, List


class AutonomousSystem(Printable, Graphable, Configurable):
    """!
    @brief AutonomousSystem class. 

    This class represents an autonomous system.
    """

    __asn: int
    __subnets: List[IPv4Network]
    __reg: ScopedRegistry
    __routers: Dict[str, Node]
    __hosts: Dict[str, Node]
    __nets: Dict[str, Network]

    def __init__(self, asn: int, subnetTemplate: str = "10.{}.0.0/16"):
        """!
        @brief AutonomousSystem constructor.

        @param asn ASN for this system.
        @param subnetTemplate template for assigning subnet.
        """
        self.__hosts = {}
        self.__routers = {}
        self.__nets = {}
        self.__asn = asn
        self.__subnets = None if asn > 255 else list(IPv4Network(subnetTemplate.format(asn)).subnets(new_prefix = 24))

    def registerNodes(self, simulator: Simulator):
        reg = simulator.getRegistry()
        for (key, val) in self.__hosts.items(): reg.register(str(self.__asn), 'hnode', key, val)
        for (key, val) in self.__routers.items(): reg.register(str(self.__asn), 'rnode', key, val)
        for (key, val) in self.__nets.items(): reg.register(str(self.__asn), 'net', key, val)

    def configure(self, simulator: Simulator):
        for host in self.__hosts.values(): host.configure(simulator)
        for router in self.__routers.values(): router.configure(simulator)

    def getAsn(self) -> int:
        """!
        @brief Get ASN.
        """
        return self.__asn
    
    def createNetwork(self, name: str, prefix: str = "auto", aac: AddressAssignmentConstraint = None) -> Network:
        """!
        @brief Create a new network.

        @param name name of the new network.
        @param prefix optional. Network prefix of this network. If not set, a
        /24 subnet of "10.{asn}.{id}.0/24" will be used, where asn is ASN of
        this AS, and id is a self-incremental value starts from 0.
        @param aac optional. AddressAssignmentConstraint to use.
        @throws StopIteration if subnet exhausted.
        """
        assert prefix != "auto" or self.__asn <= 255, "can't use auto: asn > 255"

        network = IPv4Network(prefix) if prefix != "auto" else self.__subnets.pop(0)
        assert name not in self.__nets, 'Network with name {} already exist.'.format(name)
        self.__nets[name] = Network(name, NetworkType.Local, network, aac)

        return self.__nets[name]

    def getNetwork(self, name: str) -> Network:
        """!
        @brief Retrive a network.

        @param name name of the network.
        @returns Network.
        """
        return self.__nets[name]

    def getNetworks(self) -> List[str]:
        """!
        @brief Get llist of name of networks.
        """
        return list(self.__nets.keys())

    def createRouter(self, name: str) -> Node:
        """!
        @brief Create a router node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__routers, 'Router with name {} already exists.'.format(name)
        self.__routers[name] = Node(name, NodeRole.Router, self.__asn)

        return self.__routers[name]

    def getRouters(self) -> List[str]:
        """!
        @brief Get llist of name of routers.
        """
        return list(self.__routers.keys())

    def getRouter(self, name: str) -> Node:
        """!
        @brief Retrive a router node.

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
        @brief Retrive a host node.

        @param name name of the node.
        @returns Node.
        """
        return self.__hosts[name]

    def getHosts(self) -> List[str]:
        """!
        @brief Get llist of name of hosts.
        """
        return list(self.__hosts.keys())

    def _doCreateGraphs(self):
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
                l2graph.addEdge(rtrname, netname)

        for obj in self.__hosts.values():
            router: Node = obj
            rtrname = 'Host: {}'.format(router.getName(), group = 'AS{}'.format(self.__asn))
            l2graph.addVertex(rtrname, group = 'AS{}'.format(self.__asn))
            for iface in router.getInterfaces():
                net = iface.getNet()
                netname = 'Network: {}'.format(net.getName())
                l2graph.addEdge(rtrname, netname)

        
    def print(self, indent: int) -> str:
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