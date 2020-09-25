from .Printable import Printable
from .Network import Network
from .AddressAssignmentConstraint import AddressAssignmentConstraint
from .Registry import ScopedRegistry
from .enums import NetworkType, NodeRole
from .Node import Node
from ipaddress import IPv4Network
from typing import Generator, Dict

class AutonomousSystem(Printable):
    """!
    @brief AutonomousSystem class. 

    This class represents an autonomous system.
    """

    __asn: int
    __subnet_generator: Generator[IPv4Network, None, None]
    __reg: ScopedRegistry

    def __init__(self, asn: int):
        """!
        @brief AutonomousSystem constructor.

        @param asn ASN for this system.
        """
        self.__asn = asn
        self.__reg = ScopedRegistry(str(asn))
        self.__subnet_generator = None if asn > 255 else IPv4Network("10.{}.0.0/16".format(asn)).subnets(new_prefix = 24)
    
    def createNetwork(self, name: str, prefix: str = "auto", aac: AddressAssignmentConstraint = None) -> Network:
        """!
        @brief Create a new network.

        @param name name of the new network.
        @param prefix optional. Network prefix of this network. If not set, a
        /24 subnet of "10.{asn}.{id}.0/24" will be used, where asn is ASN of
        this AS, and id is a self-incremental value starts from 0.
        @throws StopIteration if subnet exhausted.
        """
        assert prefix != "auto" or self.__asn <= 255, "can't use auto: asn > 255"

        network = IPv4Network(prefix) if prefix != "auto" else next(self.__subnet_generator)
        return self.__reg.register('net', name, Network(name, NetworkType.Local, network, aac))

    def getNetwork(self, name: str) -> Network:
        """!
        @brief Retrive a network.

        @param name name of the network.
        @returns Network.
        """
        return self.__reg.get('net', name)

    def createRouter(self, name: str) -> Node:
        """!
        @brief Create a router node.

        @param name name of the new node.
        @returns Node.
        """
        return self.__reg.register('rnode', name, Node(name, NodeRole.Router, self.__asn))

    def getRouter(self, name: str) -> Node:
        """!
        @brief Retrive a router node.

        @param name name of the node.
        @returns Node.
        """
        return self.__reg.get('rnode', name)

    def createHost(self, name: str) -> Node:
        """!
        @brief Create a host node.

        @param name name of the new node.
        @returns Node.
        """
        return self.__reg.register('hnode', name, Node(name, NodeRole.Host, self.__asn))

    def getHost(self, name: str) -> Node:
        """!
        @brief Retrive a host node.

        @param name name of the node.
        @returns Node.
        """
        return self.__reg.get('hnode', name)
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'AutonomousSystem {}:\n'.format(self.__asn)

        indent += 4
        out += ' ' * indent
        out += 'Networks:\n'

        for net in self.__reg.getByType('net'):
            out += net.print(indent + 4)

        out += ' ' * indent
        out += 'Routers:\n'

        for net in self.__reg.getByType('rnode'):
            out += net.print(indent + 4)

        out += ' ' * indent
        out += 'Hosts:\n'

        for net in self.__reg.getByType('hnode'):
            out += net.print(indent + 4)

        return out