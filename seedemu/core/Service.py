from __future__ import annotations
from .Layer import Layer
from .Node import Node
from .Printable import Printable
from .Emulator import Emulator
from .enums import NodeRole
from .Binding import Binding
from typing import Dict, List, Set, Tuple
from .BaseSystem import BaseSystem

class Server(Printable):
    """!
    @brief Server class.

    The Server class is the handler for installed services.
    """
    __class_names: list
    _base_system: BaseSystem
    def __init__(self):
        super().__init__()
        self.__class_names = []
        self._base_system = BaseSystem.DEFAULT

    def install(self, node: Node):
        """!
        @brief Install the server on node.

        @param node node.
        """
        raise NotImplementedError('install not implemented')
    
    def setBaseSystem(self, base_system: BaseSystem) -> Server:
        """!
        @brief Set a base_system of a server.

        @param base_system base_system to use.

        @returns self, for chaining API calls.
        """
        self._base_system = base_system
    
    def getBaseSystem(self) -> BaseSystem:
        """!
        @brief Get configured base system on this server.

        @returns base system.
        """
        return self._base_system

    def getClassNames(self):
        return self.__class_names
    
    def appendClassName(self, class_name:str):
        """!
        @brief Append Class Name
        The method called by User. 

        @param class_name class name.

        @return self.
        """

        self.__class_names.append(class_name)

        return self
        
class Service(Layer):
    """!
    @brief Service base class.

    The base class for all Services.
    """

    _pending_targets: Dict[str, Server]
    
    __targets: Set[Tuple[Server, Node]]

    def __init__(self):
        super().__init__()
        self._pending_targets = {}
        self.__targets = set()

    def _createServer(self) -> Server:
        """!
        @brief Create a new server.
        """
        raise NotImplementedError('_createServer not implemented')

    def _doInstall(self, node: Node, server: Server):
        """!
        @brief install the server on node. This can be overridden by service
        implementations.

        @param node node.
        @param server server.
        """
        server.install(node)

    def _doSetClassNames(self, node:Node, server:Server) -> Node:
        """!
        @brief set the class names on node. 

        @param node node.
        @param server server.
        """
        server.setClassNames(node)

    def _doConfigure(self, node: Node, server: Server):
        """!
        @brief configure the node. Some services may need to by configure before
        rendered.

        This is currently used by the DNS layer to configure NS and gules
        records before the actual installation.
        
        @param node node
        @param server server
        """
        return

    def __configureServer(self, server: Server, node: Node):
        """!
        @brief Configure the service on given node.

        @param node node to configure the service on.

        @throws AssertionError if node is not host node.
        """
        assert node.getRole() == NodeRole.Host, 'node as{}/{} is not a host node'.format(node.getAsn(), node.getName())
        servicesdb: Dict = node.getAttribute('services', {})

        for (name, service_info) in servicesdb.items():
            service: Service = service_info['__self']
            assert name not in self.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())
            assert self.getName() not in service.getConflicts(), '{} conflict with {} on as{}/{}.'.format(self.getName(), service.getName(), node.getAsn(), node.getName())

        m_name = self.getName()
        if m_name not in servicesdb:
            servicesdb[m_name] = {
                '__self': self
            }

        node.setBaseSystem(server.getBaseSystem())
        
        self._doConfigure(node, server)
        self.__targets.add((server, node))

    def addPrefix(self, prefix: str):
        """!
        @brief add a prefix to all virtual nodes.

        This method sets a prepend a prefix to all virtual node names.
        """
        new_dict = {}
        for k, v in self._pending_targets.items():
            new_dict[prefix + k] = v
        
        self._pending_targets = new_dict

    def install(self, vnode: str) -> Server:
        """!
        @brief install the service on a node identified by given name.
        """
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]

    def configure(self, emulator: Emulator):
        for (vnode, server) in self._pending_targets.items():
            pnode = emulator.getBindingFor(vnode)
            self._log('looking for binding for {}...'.format(vnode))
            self.__configureServer(server, pnode)
            self._log('configure: bound {} to as{}/{}.'.format(vnode, pnode.getAsn(), pnode.getName()))
    
    def render(self, emulator: Emulator):
        for (server, node) in self.__targets:
            self._doInstall(node, server)
            for className in server.getClassNames():
                node.appendClassName(className)
        
    def getConflicts(self) -> List[str]:
        """!
        @brief Get a list of conflicting services.

        Override to change.

        @return list of service names.
        """
        return []

    def getTargets(self) -> Set[Tuple[Server, Node]]:
        """!
        @brief Get nodes and the server object associated with them. Note this
        only work after the layer is configured.
        """
        return self.__targets

    def setPendingTargets(self, targets: Dict[str, Server]):
        """!
        @brief Overrides the pending vnode dict. Use with caution.

        @param targets new targets.
        """
        self._pending_targets = targets

    def getPendingTargets(self) -> Dict[str, Server]:
        """!
        @brief Get a set of pending vnode to install the service on.
        """
        return self._pending_targets

