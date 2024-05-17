from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType
from seedemu.services.EthereumService import *
from os import path
from .FaucetUtil import FaucetServerFileTemplates
from seedemu.services.EthereumService import *


class FaucetServer(Server):
    """!
    @brief The FaucetServer class.
    """
    
    __blockchain:Blockchain
    __port: int
    __balance: int
    __eth_server_url: str
    __eth_server_port: int
    __linked_eth_node:str
    __chain_id: int
    __consensus: ConsensusMechanism
    __max_fund_amount: int
    __max_fund_attemps: int

    def __init__(self, blockchain:Blockchain, linked_eth_node:str, port:int, balance:int, max_fund_amount:int):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        from eth_account import Account
        self.__Account = Account
        self.__blockchain = blockchain
        self.__port = port
        self.__account = self.__Account.from_key('0xa9aec7f51b6b872d86676d4e5facf4ddf6850745af133b647781d008894fa3aa')
        self.__balance = balance
        self.__balance_unit = EthUnit.ETHER
        self.__eth_server_url = ''
        self.__linked_eth_node = linked_eth_node
        self.__chain_id = blockchain.getChainId()
        self.__fundlist = []
        self.__consensus = blockchain.getConsensusMechanism()
        self.__max_fund_amount = max_fund_amount
        self.__max_fund_attempts = 30
    
    def setOwnerPrivateKey(self, keyString: str, isEncrypted = False, password = ""):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        if isEncrypted:
            self.__account =self.__Account.from_key(self.__Account.decrypt(keyfile_json=keyString,password=password))
        else:
            self.__account =self.__Account.from_key(keyString)
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
            self.__account =self.__Account.from_key(self.__Account.decrypt(keyfile_json=keyfileContent,password=password))
        else: 
            self.__account =self.__Account.from_key(keyfileContent)
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
    
    def setLinkedEthNode(self, vnodeName:str):
        self.__linked_eth_node = vnodeName
        return self

    def setEthServerUrl(self, url:str):
        self.__eth_server_url = url
        return self
    
    def getEthServerUrl(self):
        return self.__eth_server_url
    
    def setEthServerPort(self, port:int):
        self.__eth_server_port = port
        return self
    
    def getEthServerPort(self):
        return self.__eth_server_port
        
    def getLinkedEthNodeName(self) -> str:
        return self.__linked_eth_node
    
    def getBlockchain(self) -> str:
        return self.__blockchain
    
    def getFaucetAddress(self) -> str:
        return self.__account.address
    
    def getFaucetBalance(self) -> int:
        return self.__balance
    
    def getPort(self) -> int:
        return self.__port
    
    def setFundMaxAttempts(self, attempts:int) -> FaucetServer:
        self.__max_fund_attempts = attempts
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetService")

        # self.__blockchain.addLocalAccount(self.__account.address, balance=self.__balance)
        node.addSoftware('python3 python3-pip')
        
        node.addBuildCommand('pip3 install flask web3==5.31.1')
        # node.setFile('/var/www/html/index.html', self.__index.format(asn = node.getAsn(), nodeName = node.getName()))
        node.setFile('/app.py', FaucetServerFileTemplates['faucet_server'].format(max_fund_amount=self.__max_fund_amount,
                                                                                  chain_id=self.__chain_id,
                                                                                  eth_server_url = self.__eth_server_url, 
                                                                                  eth_server_http_port = self.__eth_server_port,
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
                                                                                 max_attempts = self.__max_fund_attempts,
                                                                                 port=self.__port,
                                                                                 fund_command=';'.join(funds_list)))
        node.appendStartCommand('chmod +x /fund.sh')
        node.appendStartCommand('/fund.sh')
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Faucet server object.\n'

        return out
