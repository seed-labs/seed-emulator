from __future__ import annotations
from .Printable import Printable
from .Emulator import Emulator
from .Node import Node
from .Filter import Filter
from .BaseSystem import BaseSystem
from enum import Enum
from typing import List
from ipaddress import IPv4Network, IPv4Address
from sys import stderr
import re, random, string
from .Scope import Scope, NodeScopeTier

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

    ## create a node matching the given conditions. Note that 'NEW' nodes are
    # only created during render, and attempt to resolve it beforehand
    # (like resolvVnode) is not possible.
    NEW = 3


class Binding(Printable):
    """!
    @brief Binding class. 

    A binding class defines how to bind virtual nodes to physical nodes.
    """

    source: str
    action: Action
    filter: Filter

    def __init__(self, source, action = Action.RANDOM, filter = Filter()):
        """!
        @brief create new binding.

        @param source virtual node name. can be regexp to match multiple virtual
        nodes.
        @param action (optional) candidate selection. Default to random.
        @param filter (optional) filter. Default to empty filter (all physical
        nodes).
        """

        ## regexp of virtual node name that should be handled by this binding.
        self.source = source

        ## candidate selection after the filter completes.
        self.action = action

        ## physical node filter.
        self.filter = filter

    def __filterBaseSystemConflict(self, vnode:str, node:Node, emulator:Emulator) -> bool:
        """!
        @brief filter a base_system conflict between vnode and node when binding. 

        @param vnode virtual node name.
        @param node candidate physical name to bind with vnode.
        @param emulator emulator instance to get server object by vnode name.

        @returns True if it does not have any conflict.
        """
        nodeBaseSystem = node.getBaseSystem()
        server = emulator.getServerByVirtualNodeName(vnode)
        vnodeBaseSystem = server.getBaseSystem()
        if nodeBaseSystem == vnodeBaseSystem:
            return True
        if BaseSystem.doesAContainB(A=vnodeBaseSystem, B=nodeBaseSystem):
            return True
        if BaseSystem.doesAContainB(A=nodeBaseSystem, B=vnodeBaseSystem):
            server.setBaseSystem(nodeBaseSystem)
            return True
        
        return False
    
    def __create(self, emulator: Emulator) -> Node:
        """!
        @brief create a node matching given condition.

        @returns node created.
        """
        self.__log('binding: NEW: try to create a node matching filter condition(s)...')

        reg = emulator.getRegistry()

        base = emulator.getLayer('Base')

        f = self.filter

        assert f.custom == None, 'binding: NEW: custom filter function is not supported with NEW action.'
        assert f.asn == None or f.asn in base.getAsns(), 'binding: NEW: AS{} is set in filter but not in emulator.'.format(f.asn)
        assert f.ip == None or f.prefix == None, 'binding: NEW: both ip and prefix is set. Please set only one of them.'

        if f.allowBound: self.__log('binding: NEW: WARN: allowBound has not effect when using Action.NEW')

        asn = f.asn
        netName = None

        # ip is set: find net matching the condition.
        if f.ip != None:
            self.__log('binding: NEW: IP {} is given to host: finding networks with this IP in range.'.format(f.ip))
            for _asn in base.getAsns():
                hit = False
                if f.asn != None and f.asn != _asn: continue
                
                asObject = base.getAutonomousSystem(_asn)
                for net in asObject.getNetworks():
                    netObject = asObject.getNetwork(net)

                    if IPv4Address(f.ip) in netObject.getPrefix():
                        self.__log('match found: as{}/{}'.format(_asn, net))
                        asn = _asn
                        netName = net
                        hit = True
                        break

                if hit: break
        
        # prefix is set: find net matching the condition
        if f.prefix != None:
            self.__log('binding: NEW: Prefix {} is given to host: finding networks in range.'.format(f.prefix))

            for _asn in base.getAsns():
                hit = False
                if f.asn != None and f.asn != _asn: continue
                
                asObject = base.getAutonomousSystem(_asn)
                for net in asObject.getNetworks():
                    netObject = asObject.getNetwork(net)

                    if IPv4Network(f.prefix).overlaps(netObject.getPrefix()):
                        self.__log('binding: NEW: match found: as{}/{}'.format(_asn, net))
                        asn = _asn
                        netName = net
                        hit = True
                        break

                if hit: break

        if f.prefix != None or f.ip != None:
            assert netName != None, 'binding: NEW: cannot satisfy prefix/ip rule set by filter.'
        
        # no as selected: randomly choose one
        if asn == None:
            asn = random.choice(base.getAsns())
            self.__log('binding: NEW: asn not set, using random as: {}'.format(asn))

        asObject = base.getAutonomousSystem(asn)

        # no net selected: randomly choose one
        if netName == None:
            netName = random.choice(asObject.getNetworks())
            self.__log('binding: NEW: ip/prefix not set, using random net: as{}/{}'.format(asn, netName))


        nodeName = f.nodeName
        
        # no nodename given: randomly create one
        if nodeName == None:
            nodeName = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
            self.__log('binding: NEW: nodeName not set, using random name: {}'.format(nodeName))

        self.__log('binding: NEW: creating new host...'.format(nodeName))

        # create the host in as
        host = asObject.createHost(nodeName)
        # inherit AS level option overrides...
        asObject.handDown(host)
        # 'host' didnt exist back when Base::configure() installed
        #  the global default sysctl options on all nodes
        for o in base.getAvailableOptions():
            host.setOption(o, Scope(NodeScopeTier.Global))

        # set name servers
        host.setNameServers(asObject.getNameServers())

        # join net
        host.joinNetwork(netName, 'auto' if f.ip == None else f.ip)

        # register - usually this is done by AS in configure stage, since we have passed that point, we need to do it ourself.
        reg.register(str(asn), 'hnode', nodeName, host)

        # configure - usually this is done by AS in configure stage, since we have passed that point, we need to do it ourself.
        # >> here at the latest,  any relevant options must be set on the node or they wont be considered
        host.configure(emulator)
        return host


    def shoudBind(self, vnode: str) -> bool:
        """!
        @brief test if this binding applies to a virtual node.

        @param vnode name of vnode.

        @returns true if applies, false otherwise.
        """
        return re.compile(self.source).match(vnode)

    def getCandidate(self, vnode: str, emulator: Emulator, peek: bool = False) -> Node:
        """!
        @brief get a binding candidate from given emulator. Note that this will
        make change to the node by adding a "bound =  true" attribute to the
        node object.

        @param vnode name of vnode
        @param emulator emulator to select candidate from. 
        @param peek (optional) peek mode - ignore bound attribute and don't set
        it when node is selected.

        @return candidate node, or none if not found.
        """
        if not self.shoudBind(vnode): return None
        self.__log('looking for binding for {}'.format(vnode))

        if self.action == Action.NEW:
            if peek: return None

            node = self.__create(emulator)
            node.setAttribute('bound', True)

            return node
            
        registry = emulator.getRegistry()

        candidates: List[Node] = []

        for (scope, type, name), obj in registry.getAll().items():
            if type not in ['hnode', 'rnode', 'csnode']: continue
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
                    if iface.getAddress() in net:
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
            
            if not self.__filterBaseSystemConflict(vnode, node, emulator):
                self.__log('node as{}/{} base_system is not compatible'.format(scope, name))
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