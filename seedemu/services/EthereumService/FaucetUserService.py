
from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.services.EthereumService import *
from .FaucetUtil import *

# This service is a base code of a service utilizing faucetServer.


class FaucetUserServer(Server):
    """!
    @brief The FaucetServer class.
    """
    DIR_PREFIX = "faucet_user"

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
        self.__faucet_util.setFaucetServerInfo(vnode=self.__faucet_vnode_name, 
                                               port=self.__faucet_port)
        self.__faucet_util.configure(emulator)

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetUserService")
        node.addSoftware('python3 python3-pip')
        node.addBuildCommand('pip3 install eth_account==0.5.9 requests')
        node.setFile(self.DIR_PREFIX + '/fundme.py', 
                     FaucetServerFileTemplates['fundme'].format(
                           faucet_url=self.__faucet_util.getFacuetUrl(),
                           faucet_fund_url=self.__faucet_util.getFaucetFundUrl()))
        node.appendStartCommand('chmod +x {}/fund.py'.format(self.DIR_PREFIX))
        node.appendStartCommand(self.DIR_PREFIX + '/fund.py')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Faucet user server object.\n'

        return out

class FaucetUserService(Service):
    """!
    @brief The FaucetUserService class.
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
    
