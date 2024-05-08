from seedemu import *
from typing import Dict, List
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService import ChainlinkInitializerServer, ChainlinkServer

    
class ChainlinkService(Service):
    """
    @brief The Chainlink service class.
    """
    __faucet_vnode_name: str
    __faucet_port: int
    __chainlink_servers = []
    __chainlink_init_server = ""
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
        if self.__chainlink_init_server != "":
            raise TypeError("Chainlink initializer server already installed.")
        
        if vnode in self._pending_targets.keys(): 
            return self._pending_targets[vnode]

        s = self._createInitializerServer()
        self._pending_targets[vnode] = s
        return self._pending_targets[vnode]
    
    def _doInstall(self, node: Node, server: Server):
        install_implemented = 'install' in server.__class__.__dict__
        installInitializer_implemented = 'installInitializer' in server.__class__.__dict__
        
        if install_implemented and installInitializer_implemented:
            raise TypeError("Server class must override either 'install' or 'installInitializer', not both.")
        elif not install_implemented and not installInitializer_implemented:
            raise TypeError("Server class must override one of 'install' or 'installInitializer'.")

        if install_implemented:
            server.install(node, self.__faucet_vnode_name, self.__faucet_port, self.getChainlinkInitServerName())
        elif installInitializer_implemented:
            server.installInitializer(node, self.__faucet_vnode_name, self.__faucet_port)
            
    def configure(self, emulator: Emulator):
        super().configure(emulator)
        targets = self.getTargets()
        for (server, node) in targets:
            server.configure(node, emulator)
    
    def setFaucetServerInfo(self, vnode: str, port: int = 80):
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port
        return self
    
    def getChainlinkInitServerName(self) -> str:
        """
        @brief Get the name of the Chainlink initializer server.
        
        @return The string name of the Chainlink initializer server.
        """
        pending_targets = self._pending_targets
        for key, value in pending_targets.items():
            if isinstance(value, ChainlinkInitializerServer):
                self.__chainlink_init_server = key
                
        return self.__chainlink_init_server
            
    def getChainlinkServerNames(self) -> List[str]:
        """
        @brief Get the names of the Chainlink servers.
        
        @return The list names of the Chainlink servers.
        """
        chainlink_server_names = []
        pending_targets = self._pending_targets
        for key, value in pending_targets.items():
            if isinstance(value, ChainlinkServer):
                chainlink_server_names.append(key)
        
        self.__chainlink_servers = chainlink_server_names
        return self.__chainlink_servers

    def getName(self) -> str:
        return 'ChainlinkService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ChainlinkServiceLayer\n'
        return out