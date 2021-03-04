from seedsim.core import Printable, Node, Registry
from enum import Enum
from typing import List, Callable, Literal
from ipaddress import IPv4Network
import re, random

class Action(Enum):
    RANDOM = 0
    FIRST = 1
    LAST = 2

class Filter(Printable):
    asn: int
    nodeName: str
    ip: str
    prefix: str
    anyService: List[str]
    allServices: List[str]
    notServices: List[str]

    custom: Callable[[str, Node], bool]

    def __init__(
        self, asn: int = None, nodeName: str = None, ip: str = None,
        prefix: str = None, anyService: List[str] = [], allServices: List[str] = [],
        notServices: List[str] = [], custom: Callable[[str, Node], bool] = None
    ):
        self.asn = asn
        self.nodeName = nodeName
        self.ip = ip
        self.prefix = prefix
        self.anyService = anyService
        self.allServices = allServices
        self.notServices = notServices
        self.custom = custom

class Binding(Printable):

    souce: str
    action: Action
    filter: Filter

    def __init__(self, source, action = Action.RANDOM, filter = Filter()):
        self.souce = source
        self.action = action
        self.filter = filter

    def shoudBind(self, vnode: str) -> bool:
        """!
        @brief test if this binding applies to a virtual node.

        @param vnode name of vnode.

        @returns true if applies, false otherwise
        """
        return re.compile(self.souce).match(vnode)

    def getCandidate(self, vnode: str, registry: Registry) -> Node:
        """!
        @brief get a binding candidate from given registry. Note that this will
        make change to the node by adding a "binded =  true" attribute to the
        node object.

        @param vnode name of vnode
        @param regitry registry to select candidate from. 

        @return candidate node, or none if not found
        """
        if not self.shoudBind(vnode): return None

        candidates: List[Node] = []

        for (scope, type, name), obj in registry.getAll().items():
            if type != 'hnode': continue
            node: Node = obj
            filter = self.filter

            if filter.asn != None and node.getAsn() != filter.asn: continue
            
            if filter.nodeName != None and not re.compile(filter.nodeName).match(name): continue

            if filter.ip != None:
                has_match = False
                for iface in node.getInterfaces():
                    if str(iface.getAddress()) == filter.ip:
                        has_match = True
                        break
                if not has_match: continue

            if filter.prefix != None:
                has_match = False
                net = IPv4Network(filter.prefix)
                for iface in node.getInterfaces():
                    if iface.getAddress() in net.hosts():
                        has_match = True
                        break
                if not has_match: continue

            node_services = node.getAttribute('services', {}).keys()

            if len(filter.anyService) > 0 and not any([ x in node_services for x in filter.anyService ]): continue

            if len(filter.allServices) > 0 and not all([ x in node_services for x in filter.allServices ]): continue

            if len(filter.notServices) > 0 and any([ x in node_services for x in filter.notServices ]): continue

            if filter.custom != None and not filter.custom(vnode, node): continue

            if node.hasAttribute('binded'): continue

            if self.action == Action.FIRST:
                node.setAttribute('binded', True)
                return node
        
            candidates.append(node)

        if len(candidates) == 0: return None

        if self.action == Action.LAST: return candidates[-1]

        if self.action == Action.RANDOM: return random.choice(candidates)

        return None

