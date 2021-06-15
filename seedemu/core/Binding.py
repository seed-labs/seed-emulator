from seedemu.core import Printable, Node, Registry
from enum import Enum
from typing import List, Callable
from ipaddress import IPv4Network
from sys import stderr
import re, random

class Action(Enum):
    """!
    @brief actions to take when a binding matches a node.
    """

    ## pick randomly from the candidates.
    RANDOM = 0

    ## pick the first candidate.
    FIRST = 1

    ## pick the last candidate.
    LAST = 2

class Filter(Printable):
    """!
    @brief the Filter class.

    The filter class is used to define some conditions to narrow down candidates
    for a binding.
    """

    ## asn of node
    asn: int

    ## name of node
    nodeName: str

    ## ip address of node (w/o mask)
    ip: str

    ## prefix range of node's IP address
    prefix: str

    ## allow re-use already bound nodes
    allowBound: bool

    ## custom test function
    custom: Callable[[str, Node], bool]

    def __init__(
        self, asn: int = None, nodeName: str = None, ip: str = None,
        prefix: str = None, custom: Callable[[str, Node], bool] = None,
        allowBound: bool = False
    ):
        """!
        @brief create new filter.
        
        If no options are given, the filter matches all nodes in the emulation.
        If more then one options are given, the options are joined with "and"
        operation - meaning the node must match all given options to be
        selected.

        @param asn (optional) asn of node. Default to None (any ASN).
        @param nodeNmae (optional) name of node. Default to None (any name).
        @param ip (optional) IP address of node (w/o mask). Default to None (any
        IP).
        @param prefix (optional) Prefix range of node's IP address (CIDR).
        Default to None (any prefix).
        @param custom (optional) custom test function. Must accepts
        (virtual_node_name, physical_node_object) as input and returns a bool.
        Default to None (always allow).
        @param allowBound (optional) allow re-use bound nodes. Default to false.
        """

        self.asn = asn
        self.nodeName = nodeName
        self.ip = ip
        self.prefix = prefix
        self.custom = custom
        self.allowBound = allowBound

class Binding(Printable):
    """!
    @brief Binding class. 

    A binding class defines how to bind virtual nodes to physical nodes.
    """

    ## regexp of virtual node name that should be handlded by this binding.
    source: str

    ## candidate selection after the filter completes.
    action: Action

    ## physical node filter.
    filter: Filter

    def __init__(self, source, action = Action.RANDOM, filter = Filter()):
        """!
        @brief create new binding.

        @param source virtual node name. can be regexp to match mutiple virtual
        nodes.
        @param action (optional) candidate selection. Default to random.
        @param filter (optional) filter. Default to empty filter (all physical
        nodes).
        """
        self.source = source
        self.action = action
        self.filter = filter

    def shoudBind(self, vnode: str) -> bool:
        """!
        @brief test if this binding applies to a virtual node.

        @param vnode name of vnode.

        @returns true if applies, false otherwise.
        """
        return re.compile(self.source).match(vnode)

    def getCandidate(self, vnode: str, registry: Registry, peek: bool = False) -> Node:
        """!
        @brief get a binding candidate from given registry. Note that this will
        make change to the node by adding a "bound =  true" attribute to the
        node object.

        @param vnode name of vnode
        @param regitry registry to select candidate from. 
        @param peek (optional) peek mode - ignore bound attribute and don't set
        it when node is selected.

        @return candidate node, or none if not found.
        """
        if not self.shoudBind(vnode): return None
        self.__log('looking for binding for {}'.format(vnode))

        candidates: List[Node] = []

        for (scope, type, name), obj in registry.getAll().items():
            if type != 'hnode': continue
            node: Node = obj
            filter = self.filter

            self.__log('trying node as{}/{}...'.format(scope, name  ))

            if filter.asn != None and node.getAsn() != filter.asn:
                self.__log('node asn ({}) != filter asn ({}), trying next node.'.format(node.getAsn(), filter.asn))
                continue
            
            if filter.nodeName != None and not re.compile(filter.nodeName).match(name):
                self.__log('node name ({}) cat\'t match filter name ({}), trying next node.'.format(name, filter.nodeName))
                continue

            if filter.ip != None:
                has_match = False
                for iface in node.getInterfaces():
                    if str(iface.getAddress()) == filter.ip:
                        has_match = True
                        break
                if not has_match:
                    self.__log('node as{}/{} does not have IP {}, trying next node.'.format(scope, name, filter.ip))
                    continue

            if filter.prefix != None:
                has_match = False
                net = IPv4Network(filter.prefix)
                for iface in node.getInterfaces():
                    if iface.getAddress() in net.hosts():
                        has_match = True
                        break
                if not has_match:
                    self.__log('node as{}/{} not in prefix {}, trying next node.'.format(scope, name, filter.prefix))
                    continue

            if filter.custom != None and not filter.custom(vnode, node):
                self.__log('custom function returned false for node as{}/{}, trying next node.'.format(scope, name))
                continue

            if node.hasAttribute('bound') and not filter.allowBound and not peek:
                self.__log('node as{}/{} is already bound and re-bind is not allowed, trying next node.'.format(scope, name))
                continue

            self.__log('node as{}/{} added as candidate. looking for more candidates.'.format(scope, name))

            if self.action == Action.FIRST:
                self.__log('{} as{}/{}.'.format('peek: picked' if peek else 'bound to', node.getAsn(), node.getName()))
                if not peek: node.setAttribute('bound', True)
                return node
        
            candidates.append(node)

        if len(candidates) == 0: return None

        node = None

        if self.action == Action.LAST: node = candidates[-1]

        if self.action == Action.RANDOM: node = random.choice(candidates)

        if node != None: 
            self.__log('{} as{}/{}.'.format('peek: picked' if peek else 'bound to', node.getAsn(), node.getName()))
            if not peek: node.setAttribute('bound', True)

        return node

    def __log(self, message: str):
        """!
        @brief log to stderr.

        @param message message.
        """
        print('==== Binding: {}: {}'.format(self.source, message), file=stderr)