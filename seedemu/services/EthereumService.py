#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from seedemu.core import Node, Service, Server
from typing import Dict, List
from .GenesisPoW import genesis

from eth_account import Account
import json
from datetime import datetime, timezone
from hexbytes import HexBytes

ETHServerFileTemplates: Dict[str, str] = {}

# bootstraper: get enode urls from other eth nodes.
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

class EthAccount():
    """
    @brief Ethereum Local Account.
    """

    address: str    # account address
    key: HexBytes   # account private key
    keystore_content: str   # the content of keystore file
    keystore_filename:str   # the name of keystore file 
    alloc_balance: str
    account: Account

    def __init__(self, alloc_balance:str = "0",password:str = "admin") -> None:
        """
        @brief create a Ethereum Local Account when initialize
        """
        self.account = Account.create()
        self.address = self.account.address
        self.alloc_balance = alloc_balance
        # encrypt private for Ethereum Client, like geth and generate the content of keystore file
        encrypted = Account.encrypt(self.account.key, password=password)
        self.keystore_content = json.dumps(encrypted)
        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        self.keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]    

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
    __geth_http_port: int
    __smart_contract: SmartContract
    __start_Miner_node: bool
    __create_new_account: int
    __enable_external_connection: bool
    __unlockAccounts: bool
    __predefine_accounts: List[EthAccount]

    def __init__(self, id: int):
        """!
        @brief create new eth server.

        @param id serial number of this server.
        """
        self.__id = id
        self.__is_bootnode = False
        self.__bootnode_http_port = 8088
        self.__geth_http_port = 8545
        self.__smart_contract = None
        self.__start_Miner_node = False
        self.__create_new_account = 0
        self.__enable_external_connection = False
        self.__unlockAccounts = False
        self.__predefine_accounts = []

    def __createNewAccountCommand(self, node: Node):
        if self.__create_new_account > 0:
            """!
            @brief generates a shell command which creates a new account in ethereum network.
    
            @param ethereum node on which we want to deploy the changes.
            
            """
            command = " sleep 20\n\
            geth --password /tmp/eth-password account new \n\
            "

            for count in range(self.__create_new_account):
                node.appendStartCommand('(\n {})&'.format(command))

    def __unlockAccountsCommand(self, node: Node):
        if self.__unlockAccounts:
            """!
            @brief automatically unlocking the accounts in a node.
            Currently used to automatically be able to use our emulator using Remix.
            """

            base_command = "sleep 20\n\
            geth --exec 'personal.unlockAccount(eth.accounts[{}],\"admin\",0)' attach\n\
            "
            
            full_command = ""
            for i in range(self.__create_new_account + 1):
                full_command += base_command.format(str(i))

            node.appendStartCommand('(\n {})&'.format(full_command))

    def __addMinerStartCommand(self, node: Node):
        if self.__start_Miner_node:
            """!
            @brief generates a shell command which start miner as soon as it the miner is booted up.
            
            @param ethereum node on which we want to deploy the changes.
            
            """   
            command = " sleep 20\n\
            geth --exec 'eth.defaultAccount = eth.accounts[0]' attach \n\
            geth --exec 'miner.start(1)' attach \n\
            "
            node.appendStartCommand('(\n {})&'.format(command))

    def __deploySmartContractCommand(self, node: Node):
        if self.__smart_contract != None :
            smartContractCommand = self.__smart_contract.generateSmartContractCommand()
            node.appendStartCommand('(\n {})&'.format(smartContractCommand))

    def install(self, node: Node, eth: 'EthereumService', allBootnode: bool):
        """!
        @brief ETH server installation step.

        @param node node object
        @param eth reference to the eth service.
        @param allBootnode all-bootnode mode: all nodes are boot node.
        """
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has not interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())
        this_url = '{}:{}'.format(addr, self.getBootNodeHttpPort())
        # get other nodes IP for the bootstrapper.
        bootnodes = eth.getBootNodes()[:]
        if this_url in bootnodes: bootnodes.remove(this_url)
        
        isEthereumNode = len(bootnodes) > 0

        # import keystore file to /tmp/keystore
        if len(self.__predefine_accounts) > 0:
            for account in self.__predefine_accounts:
                node.appendFile("/tmp/keystore/"+account.keystore_filename, account.keystore_content)
        
        # update genesis.json for allocating balance
        if len(eth.getAllPredefineAccounts()) > 0:
            global genesis
            genesisJson = json.loads(genesis)
            alloc_dict = dict()
            for account in eth.getAllPredefineAccounts():
                alloc_dict[account.address[2:]] = {"balance":"{}".format(account.alloc_balance)}
            genesisJson["alloc"] = alloc_dict
            genesis = json.dumps(genesisJson)

        node.appendFile('/tmp/eth-genesis.json', genesis)
        node.appendFile('/tmp/eth-nodes', '\n'.join(eth.getBootNodes()[:]))
        node.appendFile('/tmp/eth-bootstrapper', ETHServerFileTemplates['bootstrapper'])
        node.appendFile('/tmp/eth-password', 'admin') 

        node.addSoftware('software-properties-common')

        # tap the eth repo
        node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')

        # install geth and bootnode
        node.addBuildCommand('apt-get update && apt-get install --yes geth bootnode')

        # set the data directory
        datadir_option = "--datadir /root/.ethereum"

        # genesis
        node.appendStartCommand('[ ! -e "/root/.ethereum/geth/nodekey" ] && geth {} init /tmp/eth-genesis.json'.format(datadir_option))

        # create account via pre-defined password
        node.appendStartCommand('[ -z `ls -A /root/.ethereum/keystore` ] && geth {} --password /tmp/eth-password account new'.format(datadir_option))
         
        if allBootnode or self.__is_bootnode:
            # generate enode url. other nodes will access this to bootstrap the network.
            # Default port is 30301, you can change the custom port with the next command
            node.appendStartCommand('echo "enode://$(bootnode -nodekey /root/.ethereum/geth/nodekey -writeaddress)@{}:30301" > /tmp/eth-enode-url'.format(addr))
            # Default port is 30301, use -addr :<port> to specify a custom port
            node.appendStartCommand('bootnode -nodekey /root/.ethereum/geth/nodekey -verbosity 9 -addr {}:30301 > /tmp/bootnode-logs &'.format(addr))          
            # host the eth-enode-url for other nodes.
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self.__bootnode_http_port), True)

        # load enode urls from other nodes
        node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
        if not(eth.isManual()):
            node.appendStartCommand('/tmp/eth-bootstrapper')
        
        # launch Ethereum process.
        # Base common geth flags
        base_port = 30301 + self.__id
        common_flags = '{} --identity="NODE_{}" --networkid=10 --verbosity=2 --allow-insecure-unlock --port {} --http --http.addr 0.0.0.0 --http.port {}'.format(datadir_option, self.__id, base_port,  self.getGethHttpPort())
        
        # Flags updated to accept external connections
        if self.externalConnectionEnabled():
            whitelist_flags = "--http.corsdomain 'https://remix.ethereum.org' --http.api web3,eth,debug,personal,net"
            common_flags = '{} {}'.format(common_flags, whitelist_flags)
        
        # Base geth command
        geth_command = 'nice -n 19 geth {}'.format(common_flags)
        
        # Manual vs automated geth command execution
        # In the manual approach, the geth command is only thrown in a file in /tmp/run.sh
        # In the automated approach, the /tmp/run.sh file is executed by the start.sh (Virtual node) 
        
        # Echoing the geth command to /tmp/run.sh in each container
        node.appendStartCommand('echo \'{} --bootnodes "$(cat /tmp/eth-node-urls)"\' > /tmp/run.sh'.format(geth_command), True) 
       
        # Making run.sh executable
        node.appendStartCommand('sleep 10')
        node.appendStartCommand('chmod +x /tmp/run.sh')

        # Adding /tmp/run.sh in start.sh file to automate them
        if not(eth.isManual()):
            node.appendStartCommand('/tmp/run.sh &')

            self.__createNewAccountCommand(node)
            self.__unlockAccountsCommand(node)
            self.__addMinerStartCommand(node)
            self.__deploySmartContractCommand(node)
        
        # import predefine accounts after network is initiated
        for account in self.__predefine_accounts:
            node.appendStartCommand("cp /tmp/keystore/{} /root/.ethereum/keystore/".format(account.keystore_filename),True)

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


    def enableExternalConnection(self) -> EthereumServer:
        """!
        @brief setting a node as a remix node makes it possible for the remix IDE to connect to the node
        """
        self.__enable_external_connection = True

        return self

    def externalConnectionEnabled(self) -> bool:
        """!
        @brief returns wheter a node is a remix node or not
        """
        return self.__enable_external_connection

    def createNewAccount(self, number_of_accounts = 0) -> EthereumServer:
        """!
        @brief Call this api to create a new account.

        @returns self, for chaining API calls.
        """
        self.__create_new_account = number_of_accounts or self.__create_new_account + 1
        
        return self
    
    def createNewPredefineAccount(self, balance: str = "0", number: int = 1, password: str = "admin") -> EthereumServer:
        """
        @brief Call this api to create a new predefine account with balance

        @param number the number of predefine account need to create
        @param balance the balance need to be allocated to the predefine accounts
        @param password the password of account for the Ethereum client

        @returns self
        """  
        for _ in range(number):
            account = EthAccount(balance,password)
            self.__predefine_accounts.append(account)

        return self
    
    def getPredefineAccount(self) -> List[EthAccount]:
        """
        @brief Call this api to get the predefine accounts for this node
        """

        return self.__predefine_accounts

    def unlockAccounts(self) -> EthereumServer:
        """!
        @brief This is mainly used to unlock the accounts in the remix node to make it directly possible for transactions to be 
        executed through Remix without the need to access the geth account in the docker container and unlocking manually
        """
        self.__unlockAccounts = True

        return self
        
    def startMiner(self) -> EthereumServer:
        """!
        @brief Call this api to start Miner in the node.

        @returns self, for chaining API calls.
        """
        self.__start_Miner_node = True

        return self

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
    __all_node_ips: List[str]
    __boot_node_addresses: List[str]
    __all_node_predefine_accounts: List[EthAccount]

    __save_state: bool
    __save_path: str
    
    __manual_execution: bool

    def __init__(self, saveState: bool = False, manual: bool = False, statePath: str = './eth-states'):
        """!
        @brief create a new Ethereum service.

        @param saveState (optional) if true, the service will try to save state
        of the block chain by saving the datadir of every node. Default to
        false.

        @param manual (optional) if true, the user will have to execute a shell script
        provided in the directory to trigger some commands inside the containers and start
        mining

        @param statePath (optional) path to save containers' datadirs on the
        host. Default to "./eth-states". 
        """

        super().__init__()
        self.__serial = 0
        self.__all_node_ips = []
        self.__boot_node_addresses = []
        self.__all_node_predefine_accounts = []

        self.__save_state = saveState
        self.__save_path = statePath

        self.__manual_execution = manual

    def getName(self):
        return 'EthereumService'

    def getBootNodes(self) -> List[str]:
        """
        @brief get bootnode IPs.

        @returns list of IP addresses.
        """
        return self.__all_node_ips if len(self.__boot_node_addresses) == 0 else self.__boot_node_addresses
    
    def isManual(self) -> bool:
        """
        @brief Returns whether the nodes execution will be manual or not

        @returns bool
        """
        return self.__manual_execution
    
    def getAllPredefineAccounts(self) -> List[EthAccount]:
        """
        @brief get all predefined accounts in all nodes
        
        @returns list of EthAccount
        """
        return self.__all_node_predefine_accounts

    def _doConfigure(self, node: Node, server: EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())

        if server.isBootNode():
            self._log('adding as{}/{} as bootnode...'.format(node.getAsn(), node.getName()))
            self.__boot_node_addresses.append(addr)

        if len(server.getPredefineAccount()) > 0:
            self.__all_node_predefine_accounts.extend(server.getPredefineAccount())

        if self.__save_state:
            node.addSharedFolder('/root/.ethereum', '{}/{}'.format(self.__save_path, server.getId()))

    def _doInstall(self, node: Node, server: EthereumServer):
        self._log('installing eth on as{}/{}...'.format(node.getAsn(), node.getName()))
        
        all_bootnodes = len(self.__boot_node_addresses) == 0

        if all_bootnodes:
            self._log('note: no bootnode configured. all nodes will be each other\'s boot node.')

        server.install(node, self, all_bootnodes)

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

        for node in self.getBootNodes():
            out += ' ' * indent
            out += '{}\n'.format(node)

        return out
