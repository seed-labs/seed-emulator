from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService import ChainlinkInitializerServer, ChainlinkServer

    
class ChainlinkService(Service):
    """
    @brief The Chainlink service class.
    """
    def __init__(self):
        """
        @brief ChainlinkService constructor.
        """
        super().__init__()
        self.addDependency('EthereumService', False, False)

    def _createServer(self) -> ChainlinkServer:
        self._log('Creating Chainlink server.')
        return ChainlinkServer()

    def _createInitializerServer(self) -> ChainlinkInitializerServer:
        return ChainlinkInitializerServer()
    
    def installInitializer(self, vnode:str) -> Server:
        if vnode in self._pending_targets.keys(): 
            return self._pending_targets[vnode]

        s = self._createInitializerServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]
    
    def _doInstall(self, node: Node, server: Server):
        # super()._doInstall(node, server)
        install_implemented = 'install' in server.__class__.__dict__
        installInitializer_implemented = 'installInitializer' in server.__class__.__dict__

        if install_implemented and installInitializer_implemented:
            raise TypeError("Server class must override either 'install' or 'installInitializer', not both.")
        elif not install_implemented and not installInitializer_implemented:
            raise TypeError("Server class must override one of 'install' or 'installInitializer'.")

        if install_implemented:
            server.install(node)
        elif installInitializer_implemented:
            server.installInitializer(node)
            
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