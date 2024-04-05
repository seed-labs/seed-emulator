
from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType
from seedemu.services.EthereumService import *
from eth_account import Account
from eth_account.signers.local import LocalAccount
from os import path
from .FaucetUtil import *

# This service is a mock service to show how a service can use the Faucet Service.
# This will be deleted eventually.

class FaucetUserServer(Server):
    """!
    @brief The FaucetServer class.
    """
    __faucet_util:FaucetUtil
    __faucet_port: int
    __faucet_vnode_name:set
  
    def __init__(self):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        self.__faucet_util = FaucetUtil()

    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port
        
    def configure(self, emulator:Emulator):
        self.__faucet_util.setFaucetServerInfo(vnode=self.__faucet_vnode_name, port=self.__faucet_port)
        self.__faucet_util.configure(emulator)

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetUserService")
        self.__faucet_util.addFund("0x4899DA58039396E9eC4F171aa3cB20762c1f8C6c", 2)
        self.__faucet_util.addFund("0xF5c8747aD31c8726bA4bf8C6492c07625b55eE04", 3)
        node.setFile('/fund.sh', self.__faucet_util.getFundScript())
        node.appendStartCommand('chmod +x /fund.sh')
        node.appendStartCommand('/fund.sh')
    

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Faucet user server object.\n'

        return out

class FaucetUserService(Service):
    """!
    @brief The FaucetService class.
    """
    __faucet_port: int
    __faucet_vnode_name:set
    
    def __init__(self):
        """!
        @brief FaucetUserService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port

    def _createServer(self) -> Server:
        return FaucetUserServer()
    
    def configure(self, emulator: Emulator):
        super().configure(emulator)

        for (server, node) in self.getTargets():
            server.setFaucetServerInfo(self.__faucet_vnode_name, self.__faucet_port)
            server.configure(emulator)
        return 
    
    
    def getName(self) -> str:
        return 'FaucetUserService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'FaucetUserServiceLayer\n'

        return out
    
