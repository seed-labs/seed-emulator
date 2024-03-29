from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType
from seedemu.services.EthereumService import *
from eth_account import Account
from eth_account.signers.local import LocalAccount
from os import path
from .FaucetUtil import FaucetServerFileTemplates

class FaucetServer(Server):
    """!
    @brief The FaucetServer class.
    """
    
    __port: int
    __account: LocalAccount
    __balance: int
    __rpc_url: str
    __linked_eth_node:str
    __chain_id: int
    __consensus: ConsensusMechanism

    def __init__(self):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        self.__port = 80
        self.__account = Account.from_key('0xa9aec7f51b6b872d86676d4e5facf4ddf6850745af133b647781d008894fa3aa')
        self.__balance = 1000
        self.__balance_unit = EthUnit.ETHER
        self.__rpc_url = ''
        self.__linked_eth_node = ''
        self.__chain_id = -1
        self.__fundlist = []

    
    def setOwnerPrivateKey(self, keyString: str, isEncrypted = False, password = ""):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        if isEncrypted:
            self.__account = Account.from_key(Account.decrypt(keyfile_json=keyString,password=password))
        else:
            self.__account = Account.from_key(keyString)
        return self
    
    
    def importOwnerPrivateKeyFile(self, keyfilePath:str, isEncrypted:bool = True, password = "admin"):
        """
        @brief import account from keyfile.
        
        @param keyfilePath path of keyfile.

        @param isEncrypted indicates if the keyfile is encrypted or not

        @param password password of the keyfile.

        @returns self, for chaining API calls.
        """
        
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        if isEncrypted:
            self.__account = Account.from_key(Account.decrypt(keyfile_json=keyfileContent,password=password))
        else: 
            self.__account = Account.from_key(keyfileContent)
        return self

    def fund(self, recipient, amount):
        self.__fundlist.append((recipient, amount))
        return self

    def setPort(self, port: int) -> FaucetServer:
        """!
        @brief Set HTTP port.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self

    def setRpcUrl(self, url):
        self.__rpc_url = url
        return self
    
    def getRpcUrl(self):
        return self.__rpc_url
    
    def setRpcUrlByVirtualNodeName(self, vnodeName:str):
        self.__linked_eth_node = vnodeName
        return self
        
    def getLinkedEthNodeName(self) -> str:
        return self.__linked_eth_node

    def setChainId(self, chain_id):
        self.__chain_id = chain_id
        return
    
    def setConsensusMechanism(self, consensus):
        self.__consensus = consensus
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetService")
        node.addSoftware('python3 python3-pip')
        
        node.addBuildCommand('pip3 install flask web3==5.31.1')
        # node.setFile('/var/www/html/index.html', self.__index.format(asn = node.getAsn(), nodeName = node.getName()))
        node.setFile('/app.py', FaucetServerFileTemplates['faucet_server'].format(chain_id=self.__chain_id,
                                                                                  rpc_url = self.__rpc_url, 
                                                                                  consensus= self.__consensus.value,
                                                                                  account_address = self.__account.address, 
                                                                                  account_key=self.__account.privateKey.hex(),
                                                                                  port=self.__port))
        node.appendStartCommand('python3 /app.py &')

        funds_list = []
        for recipient, amount in self.__fundlist:
            funds_list.append(FaucetServerFileTemplates['fund_curl'].format(recipient=recipient, 
                                                                            amount=amount,
                                                                            address='localhost',
                                                                            port = self.__port))
            
        node.setFile('/fund.sh', FaucetServerFileTemplates['fund_script'].format(address='localhost', 
                                                                                 port=self.__port,
                                                                                 fund_command=';'.join(funds_list)))
        node.appendStartCommand('chmod +x /fund.sh')
        node.appendStartCommand('/fund.sh')
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Web server object.\n'

        return out

class FaucetService(Service):
    """!
    @brief The FaucetService class.
    """
    __emulator:Emulator

    def __init__(self):
        """!
        @brief FaucetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return FaucetServer()
    
    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        
        return super().configure(emulator)
        
    
    def _doConfigure(self, node: Node, server: Server):
        """!
        @brief configure the node. Some services may need to by configure before
        rendered.

        This is currently used by the DNS layer to configure NS and gules
        records before the actual installation.
        
        @param node node
        @param server server
        """

        server.__class__ = FaucetServer

        linked_eth_node_name = server.getLinkedEthNodeName()

        assert linked_eth_node_name != ''  or server.getRpcUrl() !='' , 'both rpc url and eth node are not set'
        server.setRpcUrl(f'http://{self.__getIpByVnodeName(linked_eth_node_name)}:8545')
        
        return
    
    def getName(self) -> str:
        return 'FaucetService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'FaucetServiceLayer\n'

        return out
    
    def __getIpByVnodeName(self, nodename:str) -> str:
        node = self.__emulator.getBindingFor(nodename)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                return address