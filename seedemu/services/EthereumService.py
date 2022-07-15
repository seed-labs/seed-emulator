#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from enum import Enum
from os import mkdir, path, makedirs, rename
from seedemu.core import Node, Service, Server, Emulator
from typing import Dict, List, Tuple

import json
from datetime import datetime, timezone

ETHServerFileTemplates: Dict[str, str] = {}
GenesisFileTemplates: Dict[str, str] = {}
GethCommandTemplates: Dict[str, str] = {}


# bootstrapper: get enode urls from other eth nodes.
ETHServerFileTemplates['bootstrapper'] = '''\
#!/bin/bash
while read -r node; do {
    let count=0
    ok=true
    until curl -sHf http://$node/eth-enode-url > /dev/null; do {
        echo "eth: node $node not ready, waiting..."
        sleep 3
        let count++
        [ $count -gt 60 ] && {
            echo "eth: node $node failed too many times, skipping."
            ok=false
            break
        }
    }; done
    ($ok) && {
        echo "`curl -s http://$node/eth-enode-url`," >> /tmp/eth-node-urls
    }
}; done < /tmp/eth-nodes
'''

class ConsensusMechanism(Enum):
    '''
    @brief Consensus Mechanism Enum. POA for Proof of Authority, POW for Proof Of Work
    '''
    POA = 'poa'
    POW = 'pow'

GenesisFileTemplates['POA'] = '''\
{
    "config": {
        "chainId": 10,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "clique": {
        "period": 15,
        "epoch": 30000
        }
    },
    "nonce": "0x0",
    "timestamp": "0x622a4e1a",
    "extraData": "0x0",
    "gasLimit": "0x47b760",
    "difficulty": "0x1",
    "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {
    },
    "number": "0x0",
    "gasUsed": "0x0",
    "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "baseFeePerGas": null
    }
    '''

GenesisFileTemplates['POW'] = '''\
{
        "nonce":"0x0",
        "timestamp":"0x621549f1",
        "parentHash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData":"0x",
        "gasLimit":"0x80000000",
        "difficulty":"0x0",
        "mixhash":"0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase":"0x0000000000000000000000000000000000000000",
        "number": "0x0",
        "gasUsed": "0x0",
        "baseFeePerGas": null,
        "config": {
            "chainId": 10,
            "homesteadBlock": 0,
            "eip150Block": 0,
            "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock": 0,
            "constantinopleBlock": 0,
            "petersburgBlock": 0,
            "istanbulBlock": 0,
            "ethash": {
            }
        },
        "alloc": {
        }
}
'''

GenesisFileTemplates['POA_extra_data'] = '''\
0x0000000000000000000000000000000000000000000000000000000000000000{signer_addresses}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'''

GethCommandTemplates['base'] = '''\
nice -n 19 geth --datadir {datadir} --identity="NODE_{node_id}" --networkid=10 --syncmode {syncmode} --snapshot={snapshot} --verbosity=2 --allow-insecure-unlock --port 30303 '''

GethCommandTemplates['mine'] = '''\
--miner.etherbase "{coinbase}" --mine --miner.threads={num_of_threads} '''

GethCommandTemplates['unlock'] = '''\
--unlock "{accounts}" --password "/tmp/eth-password" '''

GethCommandTemplates['http'] = '''\
--http --http.addr 0.0.0.0 --http.port {gethHttpPort} --http.corsdomain "*" --http.api web3,eth,debug,personal,net,clique '''

GethCommandTemplates['ws'] = '''\
--ws --ws.addr 0.0.0.0 --ws.port {gethWsPort} --ws.origins "*" --ws.api web3,eth,debug,personal,net,clique '''

GethCommandTemplates['nodiscover'] = '''\
--nodiscover '''

GethCommandTemplates['bootnodes'] = '''\
--bootnodes "$(cat /tmp/eth-node-urls)" '''

class ConsensusMechanism(Enum):
    """!
    @brief Consensus Mechanism Enum.
    """

    # POA for Proof of Authority
    POA = 'POA'
    # POW for Proof of Work
    POW = 'POW'

class Syncmode(Enum):
    """!
    @brief geth syncmode Enum.
    """
    SNAP = 'snap'
    FULL = 'full'
    LIGHT = 'light'
    

class Genesis():
    """!
    @brief Genesis manage class
    """

    __genesis:dict
    __consensusMechanism:ConsensusMechanism
    
    def __init__(self, consensus:ConsensusMechanism):
        self.__consensusMechanism = consensus
        self.__genesis = json.loads(GenesisFileTemplates[self.__consensusMechanism.value]) 


    def setGenesis(self, customGenesis:str):
        """!
        @brief set custom genesis 

        @param customGenesis genesis file contents to set. 

        @returns self, for chaining calls.
        """
        self.__genesis = json.loads(customGenesis)

        return self

    def getGenesis(self) -> str:
        """!
        @brief get a string format of genesis block.
        
        returns genesis.
        """
        return json.dumps(self.__genesis)

    def allocateBalance(self, accounts:List[EthAccount]) -> Genesis:
        """!
        @brief allocate balance to account by setting alloc field of genesis file.

        @param accounts list of accounts to allocate balance. 

        @returns self, for chaining calls.
        """
        for account in accounts:
            address = account.getAddress()
            balance = account.getAllocBalance()

            assert balance >= 0, "Genesis::allocateBalance: balance cannot have a negative value. Requested Balance Value : {}".format(account.getAllocBalance())
            self.__genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}

        return self

    def setSigner(self, accounts:List[EthAccount]) -> Genesis:
        """!
        @brief set initial signers by setting extraData field of genesis file. 
        
        extraData property in genesis block consists of 
        32bytes of vanity data, a list of iinitial signer addresses, 
        and 65bytes of vanity data.

        @param accounts account lists to set as signers.

        @returns self, for chaning API calls. 
        """

        assert self.__consensusMechanism == ConsensusMechanism.POA, 'setSigner method supported only in POA consensus.'

        signerAddresses = ''

        for account in accounts:
            signerAddresses = signerAddresses + account.getAddress()[2:]
        
        self.__genesis["extraData"] = GenesisFileTemplates['POA_extra_data'].format(signer_addresses=signerAddresses)

        return self


class EthAccount():
    """
    @brief Ethereum Local Account.
    """

    __address: str    
    __keystore_content: str  
    __keystore_filename:str  
    __alloc_balance: int
    __password: str


    def __init__(self, alloc_balance:int = 0,password:str = "admin", keyfilePath: str = None):
        """
        @brief create a Ethereum Local Account when initialize
        @param alloc_balance the balance need to be alloc
        @param password encrypt password for creating new account, decrypt password for importing account
        @param keyfile content of the keystore file. If this parameter is None, this function will create a new account, if not, it will import account from keyfile
        """
        from eth_account import Account
        self.lib_eth_account = Account

        self.__account = self.__importAccount(keyfilePath=keyfilePath, password=password) if keyfilePath else self.__createAccount()
        self.__address = self.__account.address

        assert alloc_balance >= 0, "EthAccount::__init__: balance cannot have a negative value. Requested Balance Value : {}".format(alloc_balance)
            
        self.__alloc_balance = alloc_balance
        self.__password = password

        encrypted = self.encryptAccount()
        self.__keystore_content = json.dumps(encrypted)
        
        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        self.__keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]

    def __validate_balance(self, alloc_balance:int):
        """
        validate balance
        It only allow positive decimal integer
        """
        assert alloc_balance>=0 , "Invalid Balance Range: {}".format(alloc_balance)
    
    def __importAccount(self, keyfilePath: str, password = "admin"):
        """
        @brief import account from keyfile
        """
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        return self.lib_eth_account.from_key(self.lib_eth_account.decrypt(keyfile_json=keyfileContent,password=password))
    
    def __createAccount(self):
        """
        @brief create account
        """
        return  self.lib_eth_account.create()

    def getAddress(self) -> str:
        return self.__address

    def getAllocBalance(self) -> str:
        return self.__alloc_balance

    def getKeyStoreFileName(self) -> str:
        return self.__keystore_filename

    def encryptAccount(self):
        while True:
            keystore = self.lib_eth_account.encrypt(self.__account.key, password=self.__password)
            if len(keystore['crypto']['cipherparams']['iv']) == 32:
                return keystore
                
    def getKeyStoreContent(self) -> str:
        return self.__keystore_content

    def getPassword(self) -> str:
        return self.__password


class SmartContract():

    __abi_file_name: str
    __bin_file_name: str

    def __init__(self, contract_file_bin, contract_file_abi):
        self.__abi_file_name = contract_file_abi
        self.__bin_file_name = contract_file_bin

    def __getContent(self, file_name):
        """!
        @brief get Content of the file_name.
        @param file_name from which we want to read data.
        
        @returns Contents of the file_name.
        """
        file = open(file_name, "r")
        data = file.read()
        file.close()
        return data.replace("\n","")
        

    def generateSmartContractCommand(self):
        """!
        @brief generates a shell command which deploys the smart Contract on the ethereum network.
        @param contract_file_bin binary file of the smart Contract.
        @param contract_file_abi abi file of the smart Contract.
        
        @returns shell command in the form of string.
        """
        abi = "abi = {}".format(self.__getContent(self.__abi_file_name))
        byte_code = "byteCode = \"0x{}\"".format(self.__getContent(self.__bin_file_name))
        unlock_account = "personal.unlockAccount(eth.accounts[0], \"{}\")".format("admin")
        contract_command = "testContract = eth.contract(abi).new({ from: eth.accounts[0], data: byteCode, gas: 1000000})"
        display_contract_Info = "testContract"
        finalCommand = "{},{},{},{},{}".format(abi, byte_code, unlock_account, contract_command, display_contract_Info)

        SmartContractCommand = "sleep 30 \n \
        while true \n\
        do \n\
        \t balanceCommand=\"geth --exec 'eth.getBalance(eth.accounts[0])' attach\" \n\
        \t balance=$(eval \"$balanceCommand\") \n\
        \t minimumBalance=1000000 \n\
        \t if [ $balance -lt $minimumBalance ] \n\
        \t then \n \
        \t \t sleep 60 \n \
        \t else \n \
        \t \t break \n \
        \t fi \n \
        done \n \
        echo \"Balance ========> $balance\" \n\
        gethCommand=\'{}\'\n\
        finalCommand=\'geth --exec \"$gethCommand\" attach\'\n\
        result=$(eval \"$finalCommand\")\n\
        touch transaction.txt\n\
        echo \"transaction hash $result\" \n\
        echo \"$result\" >> transaction.txt\n\
        ".format(finalCommand)
        return SmartContractCommand

class EthereumServer(Server):
    """!
    @brief The Ethereum Server
    """

    __id: int
    __is_bootnode: bool
    __bootnode_http_port: int
    __smart_contract: SmartContract
    __accounts: List[EthAccount]
    __accounts_info: List[Tuple[int, str, str]]
    __consensus_mechanism: ConsensusMechanism

    __custom_geth_binary_path: str
    __custom_geth_command_option: str

    __data_dir: str
    __syncmode: Syncmode
    __snapshot: bool
    __no_discover: bool 
    __enable_http: bool
    __geth_http_port: int
    __enable_ws: bool
    __geth_ws_port: int
    __unlock_accounts: bool
    __start_mine: bool
    __miner_thread: int
    __coinbase: str

    def __init__(self, id: int):
        """!
        @brief create new eth server.
        @param id serial number of this server.
        """
        self.__id = id
        self.__is_bootnode = False
        
        self.__bootnode_http_port = 8088
        self.__smart_contract = None
        self.__accounts = []
        self.__accounts_info = [(0, "admin", None)]
        self.__consensus_mechanism = ConsensusMechanism.POW
        self.__genesis = Genesis(self.__consensus_mechanism)

        self.__custom_geth_binary_path = None
        self.__custom_geth_command_option = None

        self.__data_dir = "/root/.ethereum"
        self.__syncmode = Syncmode.FULL
        self.__snapshot = False
        self.__no_discover = False
        self.__enable_ws = False
        self.__enable_http = False
        self.__geth_http_port = 8545
        self.__geth_ws_port = 8546
        self.__unlock_accounts = False
        self.__start_mine = False
        self.__miner_thread = 1
        self.__coinbase = ""

    def __generateGethStartCommand(self):
        """!
        @brief generate geth start commands from the properties. 

        @returns geth command. 
        """
        geth_start_command = GethCommandTemplates['base'].format(node_id=self.__id, datadir=self.__data_dir, syncmode=self.__syncmode.value, snapshot=self.__snapshot)

        if self.__no_discover:
            geth_start_command += GethCommandTemplates['nodiscover']
        else:
            geth_start_command += GethCommandTemplates['bootnodes']
        if self.__enable_http:
            geth_start_command += GethCommandTemplates['http'].format(gethHttpPort=self.__geth_http_port)
        if self.__enable_ws:
            geth_start_command += GethCommandTemplates['ws'].format(gethWsPort=self.__geth_ws_port)
        if self.__custom_geth_command_option:
            geth_start_command += self.__custom_geth_command_option
        if self.__unlock_accounts:
            accounts = []
            for account in self.__accounts:
                accounts.append(account.getAddress())
            geth_start_command += GethCommandTemplates['unlock'].format(accounts=', '.join(accounts))
        if self.__start_mine:
            assert len(self.__accounts) > 0, 'EthereumServer::__generateGethStartCommand: To start mine, ethereum server need at least one account.'
            if self.__consensus_mechanism == ConsensusMechanism.POA:
                assert self.__unlock_accounts, 'EthereumServer::__generateGethStartCommand: To start mine in POA(clique), accounts should be unlocked first.'
            geth_start_command += GethCommandTemplates['mine'].format(coinbase=self.__coinbase, num_of_threads=self.__miner_thread)
        
        return geth_start_command
    
    def install(self, node: Node, eth: EthereumService):
        """!
        @brief ETH server installation step.
        @param node node object
        @param eth reference to the eth service.
        @param allBootnode all-bootnode mode: all nodes are boot node.
        """

        node.appendClassName('EthereumService')
        node.setLabel('node_id', self.getId())
        node.setLabel('consensus', self.__consensus_mechanism.value)

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has no interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        # update genesis.json
        self.__genesis.allocateBalance(eth.getAllAccounts())
        if self.__consensus_mechanism == ConsensusMechanism.POA:
            self.__genesis.setSigner(eth.getAllSignerAccounts()) 
    
        node.setFile('/tmp/eth-genesis.json', self.__genesis.getGenesis())
    
        account_passwords = []

        for account in self.__accounts:
            node.setFile("/tmp/keystore/"+account.getKeyStoreFileName(), account.getKeyStoreContent())
            account_passwords.append(account.getPassword())

        node.setFile('/tmp/eth-password', '\n'.join(account_passwords))
            

        node.addSoftware('software-properties-common')
        # tap the eth repo
        node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')

        # install geth and bootnode
        if self.__custom_geth_binary_path : 
            node.addBuildCommand('apt-get update && apt-get install --yes bootnode')
            node.importFile("../../"+self.__custom_geth_binary_path, '/usr/bin/geth')
            node.appendStartCommand("chmod +x /usr/bin/geth")
        else:
            node.addBuildCommand('apt-get update && apt-get install --yes geth bootnode')

        # genesis
        node.appendStartCommand('[ ! -e "/root/.ethereum/geth/nodekey" ] && geth --datadir {} init /tmp/eth-genesis.json'.format(self.__data_dir))
        # copy keystore to the proper folder
        for account in self.__accounts:
            node.appendStartCommand("cp /tmp/keystore/{} /root/.ethereum/keystore/".format(account.getKeyStoreFileName()))

        if self.__is_bootnode:
            # generate enode url. other nodes will access this to bootstrap the network.
            node.appendStartCommand('[ ! -e "/root/.ethereum/geth/bootkey" ] && bootnode -genkey /root/.ethereum/geth/bootkey')
            node.appendStartCommand('echo "enode://$(bootnode -nodekey /root/.ethereum/geth/bootkey -writeaddress)@{}:30301" > /tmp/eth-enode-url'.format(addr))
            
            # Default port is 30301, use -addr :<port> to specify a custom port
            node.appendStartCommand('bootnode -nodekey /root/.ethereum/geth/bootkey -verbosity 9 -addr {}:30301 2> /tmp/bootnode-logs &'.format(addr))          
            
            # host the eth-enode-url for other nodes.
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self.__bootnode_http_port), True)
        
        # get other nodes IP for the bootstrapper.
        bootnodes = eth.getBootNodes(self.__consensus_mechanism)[:]
        if len(bootnodes) > 0 :
            node.setFile('/tmp/eth-nodes', '\n'.join(bootnodes))
            node.setFile('/tmp/eth-bootstrapper', ETHServerFileTemplates['bootstrapper'])

            # load enode urls from other nodes
            node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
            node.appendStartCommand('/tmp/eth-bootstrapper')

        # launch Ethereum process.
        node.appendStartCommand(self.__generateGethStartCommand(), True) 
       
        if self.__smart_contract != None :
            smartContractCommand = self.__smart_contract.generateSmartContractCommand()
            node.appendStartCommand('(\n {})&'.format(smartContractCommand))

    def setCustomGeth(self, customGethBinaryPath:str) -> EthereumServer:
        """
        @brief set custom geth binary file

        @param customGethBinaryPath set abosolute path of geth binary to move to the service.

        @returns self, for chaining API calls.
        """
        assert path.exists(customGethBinaryPath), "EthereumServer::setCustomGeth: custom geth binary file does not exist. path : {}".format(customGethBinaryPath)

        self.__custom_geth_binary_path = customGethBinaryPath

        return self

    def setCustomGethCommandOption(self, customOptions:str) -> EthereumServer:
        """
        @brief set custom geth start command option

        @param customOptions options to set

        @returns self, for chaining API calls.
        """
        assert customOptions.startswith("--"), "option should start with '--'"
        assert ";" not in customOptions, "letter ';' cannot contain in the options"
        assert "&" not in customOptions, "letter '|' cannot contain in the options"
        assert "|" not in customOptions, "letter '|' cannot contain in the options"

        self.__custom_geth_command_option = customOptions
        return self
        
    def setGenesis(self, genesis:str) -> EthereumServer:
        """
        @brief set custom genesis
        
        @returns self, for chaining API calls.
        """
        self.__genesis.setGenesis(genesis)

        return self

    def setSyncmode(self, syncmode:Syncmode) -> EthereumServer:
        """
        @brief setting geth syncmode (default: snap)
        
        @param syncmode use Syncmode enum options.
                Syncmode.SNAP, Syncmode.FULL, Syncmode.LIGHT

        @returns self, for chaining API calls.
        """
        self.__syncmode = syncmode
        return self

    def setNoDiscover(self, noDiscover:bool = True) -> EthereumServer:
        """
        @brief setting the automatic peer discovery to true/false
        """
        self.__no_discover = noDiscover
        return self

    def setSnapshot(self, snapshot:bool = True) -> EthereumServer:
        """!
        @breif set geth snapshot 
        
        @param snapshot bool

        @returns self, for chainging API calls.
        """
        self.__snapshot = snapshot
        return self

    def setConsensusMechanism(self, consensusMechanism:ConsensusMechanism) -> EthereumServer:
        '''
        @brief set ConsensusMechanism

        @param consensusMechanism supports POW and POA.

        @returns self, for chaining API calls. 
        '''
        self.__consensus_mechanism = consensusMechanism
        self.__genesis = Genesis(self.__consensus_mechanism)
        if consensusMechanism == ConsensusMechanism.POA:
            self.__accounts_info[0] = (32 * pow(10, 18), "admin", None)
        elif consensusMechanism == ConsensusMechanism.POW:
            self.__accounts_info[0] = (0, "admin", None)
        
        return self

    def getConsensusMechanism(self) -> ConsensusMechanism:

        return self.__consensus_mechanism

    def getId(self) -> int:
        """!
        @brief get ID of this node.
        @returns ID.
        """
        return self.__id

    def setBootNode(self, isBootNode: bool) -> EthereumServer:
        """!
        @brief set bootnode status of this node.
        Note: if no nodes are configured as boot nodes, all nodes will be each
        other's boot nodes.
        @param isBootNode True to set this node as a bootnode, False otherwise.
        
        @returns self, for chaining API calls.
        """
        self.__is_bootnode = isBootNode

        return self

    def isBootNode(self) -> bool:
        """!
        @brief get bootnode status of this node.
        @returns True if this node is a boot node. False otherwise.
        """
        return self.__is_bootnode

    def setBootNodeHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number hosting the enode url file.
        @param port port
        @returns self, for chaining API calls.
        """

        self.__bootnode_http_port = port

        return self


    def getBootNodeHttpPort(self) -> int:
        """!
        @brief get the http server port number hosting the enode url file.
        @returns port
        """

        return self.__bootnode_http_port

    def setGethHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number for normal ethereum nodes
        @param port port
        @returns self, for chaining API calls
        """
        
        self.__geth_http_port = port
        
        return self

    def getGethHttpPort(self) -> int:
        """!
        @brief get the http server port number for normal ethereum nodes
        @returns int
        """
                
        return self.__geth_http_port

    def setGethWsPort(self, port: int) -> EthereumServer:
        """!
        @brief set the ws server port number for normal ethereum nodes

        @param port port

        @returns self, for chaining API calls
        """
        
        self.__geth_ws_port = port
        
        return self

    def getGethWsPort(self) -> int:
        """!
        @brief get the ws server port number for normal ethereum nodes

        @returns int
        """
                
        return self.__geth_ws_port


    def enableGethHttp(self) -> EthereumServer:
        """!
        @brief setting a geth to enable http connection 
        """
        self.__enable_http = True

        return self

    def isGethHttpEnabled(self) -> bool:
        """!
        @brief returns whether a geth enabled http connection or not
        """
        return self.__enable_http

    def enableGethWs(self) -> EthereumServer:
        """!
        @brief setting a geth to enable ws connection
        """
        self.__enable_ws = True

        return self

    def isGethWsEnabled(self) -> bool:
        """!
        @brief returns whether a geth enabled ws connection or not
        """

        return self.__enable_ws

    def createAccount(self, balance:int=0, password:str="admin") -> EthereumServer:
        """
        @brief call this api to create new accounts

        @param balance the balance to be allocated to the account
        @param password the password to encrypt private key

        @returns self, for chaining API calls.

        """

        self.__accounts_info.append((balance, password, None))

        return self

    
    def createAccounts(self, number: int = 1, balance: int=0, password: str = "admin") -> EthereumServer:
        """
        @brief Call this api to create new accounts

        @param number the number of account need to create
        @param balance the balance need to be allocated to the accounts
        @param password the password of account for the Ethereum client

        @returns self, for chaining API calls.
        """

        for _ in range(number):    
            self.__accounts_info.append((balance, password, None))

        return self

    def _createAccounts(self, eth:EthereumService) -> EthereumServer:
        """
        @brief Call this api to create new accounts from account_info

        @returns self, for chaining API calls.
        """
        for balance, password, keyfilePath in self.__accounts_info:
            if keyfilePath:
                eth._log('importing eth account...')
            else:
                eth._log('creating eth account...')

            account = EthAccount(alloc_balance=balance,password=password, keyfilePath=keyfilePath)
            self.__accounts.append(account)

        return self    
    
    def importAccount(self, keyfilePath:str, password:str = "admin", balance: int = 0) -> EthereumServer:
        
        assert path.exists(keyfilePath), "EthereumServer::importAccount: keyFile does not exist. path : {}".format(keyfilePath)

        self.__accounts_info.append((balance, password, keyfilePath))
        return self
    
    def getAccounts(self) -> List[Tuple(int, str, str)]:
        """
        @brief Call this api to get the accounts for this node

        @returns accounts_info.
        """

        return self.__accounts_info

    def _getAccounts(self) -> List[EthAccount]:
        """
        @brief Call this api to get the accounts for this node
        
        @returns accounts
        """

        return self.__accounts
        

    def unlockAccounts(self) -> EthereumServer:
        """!
        @brief This is mainly used to unlock the accounts in the remix node to make it directly possible for transactions to be 
        executed through Remix without the need to access the geth account in the docker container and unlocking manually

        @returns self, for chaining API calls.
        """
        self.__unlock_accounts = True

        return self
        
    def startMiner(self) -> EthereumServer:
        """!
        @brief Call this api to start Miner in the node.
        @returns self, for chaining API calls.
        """
        self.__start_mine = True
        self.__syncmode = Syncmode.FULL

        return self

    def isStartMiner(self) -> bool:
        """!
        @brief call this api to get startMiner status in the node.
        
        @returns __start_mine status.
        """
        return self.__start_mine

    def deploySmartContract(self, smart_contract: SmartContract) -> EthereumServer:
        """!
        @brief Call this api to deploy smartContract on the node.
        @returns self, for chaining API calls.
        """
        self.__smart_contract = smart_contract

        return self


class EthereumService(Service):
    """!
    @brief The Ethereum network service.
    This service allows one to run a private Ethereum network in the emulator.
    """

    __serial: int
    __boot_node_addresses: Dict[ConsensusMechanism, List[str]]
    __joined_accounts: List[EthAccount]
    __joined_signer_accounts: List[EthAccount]

    __save_state: bool
    __save_path: str
    __override: bool

    def __init__(self, saveState: bool = False, savePath: str = './eth-states', override:bool=False):
        """!
        @brief create a new Ethereum service.
        @param saveState (optional) if true, the service will try to save state
        of the block chain by saving the datadir of every node. Default to
        false.

        @param savePath (optional) path to save containers' datadirs on the
        host. Default to "./eth-states". 

        @param override (optional) override the output folder if it already
        exist. False by defualt.

        """

        super().__init__()
        self.__serial = 0
        self.__boot_node_addresses = {}
        self.__boot_node_addresses[ConsensusMechanism.POW] = []
        self.__boot_node_addresses[ConsensusMechanism.POA] = []
        self.__joined_accounts = []
        self.__joined_signer_accounts = []

        self.__save_state = saveState
        self.__save_path = savePath
        self.__override = override

    def getName(self):
        return 'EthereumService'

    def getBootNodes(self, consensusMechanism:ConsensusMechanism) -> List[str]:
        """
        @brief get bootnode IPs.
        @returns list of IP addresses.
        """
        return self.__boot_node_addresses[consensusMechanism]
    
    def getAllAccounts(self) -> List[EthAccount]:
        """
        @brief Get a joined list of all the created accounts on all nodes
        
        @returns list of EthAccount
        """
        return self.__joined_accounts

    def getAllSignerAccounts(self) -> List[EthAccount]:
        return self.__joined_signer_accounts

    def _doConfigure(self, node: Node, server: EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())

        if server.isBootNode():
            self._log('adding as{}/{} as consensus-{} bootnode...'.format(node.getAsn(), node.getName(), server.getConsensusMechanism().value))
            self.__boot_node_addresses[server.getConsensusMechanism()].append(addr)
        
        server._createAccounts(self)
        
        if len(server._getAccounts()) > 0:
            self.__joined_accounts.extend(server._getAccounts())
            if server.getConsensusMechanism() == ConsensusMechanism.POA and server.isStartMiner():
                self.__joined_signer_accounts.append(server._getAccounts()[0])
            
        if self.__save_state:
            node.addSharedFolder('/root/.ethereum', '../{}/{}/ethereum'.format(self.__save_path, server.getId()))
            node.addSharedFolder('/root/.ethash', '../{}/{}/ethash'.format(self.__save_path, server.getId()))
            makedirs('{}/{}/ethereum'.format(self.__save_path, server.getId()))
            makedirs('{}/{}/ethash'.format(self.__save_path, server.getId()))
    
    def configure(self, emulator: Emulator):
        if self.__save_state:
            self._createSharedFolder()
        super().configure(emulator)
        
    def _createSharedFolder(self):
        if path.exists(self.__save_path):
            if self.__override:
                self._log('eth_state folder "{}" already exist, overriding.'.format(self.__save_path))
                i = 1
                while True:
                    rename_save_path = "{}-{}".format(self.__save_path, i)
                    if not path.exists(rename_save_path):
                        rename(self.__save_path, rename_save_path)
                        break
                    else:
                        i = i+1
            else:
                self._log('eth_state folder "{}" already exist. Set "override = True" when calling compile() to override.'.format(self.__save_path))
                exit(1)
        mkdir(self.__save_path)
        
    def _doInstall(self, node: Node, server: EthereumServer):
        self._log('installing eth on as{}/{}...'.format(node.getAsn(), node.getName()))

        server.install(node, self)

    def _createServer(self) -> Server:
        self.__serial += 1
        return EthereumServer(self.__serial)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EthereumService:\n'

        indent += 4

        out += ' ' * indent
        out += 'Boot Nodes:\n'

        indent += 4

        for node in self.getBootNodes(ConsensusMechanism.POW):
            out += ' ' * indent
            out += 'POW-{}\n'.format(node)

        for node in self.getBootNodes(ConsensusMechanism.POA):
            out += ' ' * indent
            out += 'POA-{}\n'.format(node)

        return out