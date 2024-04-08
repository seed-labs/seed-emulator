from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService import ChainlinkUserServer

 
 
class ChainlinkUserServer(Server):
    """
    @brief The Chainlink virtual user server.
    """
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator
    
    def install(self, node: Node):
        """
        @brief Install the service.
        """
        pass
    
    def __installSoftware(self):
        """
        @brief Install the software.
        """
        pass
    
    

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink user server object.\n'
        return out
 
    
class ChainlinkUserService(Service):
    """
    @brief The Chainlink service class.
    """
    def __init__(self):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('ChainlinkService', False, False)

    def _createServer(self) -> ChainlinkUserServer:
        self._log('Creating Chainlink User server.')
        return ChainlinkUserServer()
    
    def installInitializer(self, vnode:str) -> Server:
        if vnode in self._pending_targets.keys(): 
            return self._pending_targets[vnode]

        s = self._createInitializerServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]
            
    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(node, emulator)

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out
    

