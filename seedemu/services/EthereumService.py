#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from enum import Enum
from operator import ge
import os
from seedemu.core import Node, Service, Server
from typing import Dict, List

import json
from datetime import datetime, timezone
import re

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

class ConsensusMechanism(Enum):
    '''
    @brief Consensus Mechanism Enum. POA for Proof of Authority, POW for Proof Of Work
    '''
    POA = 'poa'
    POW = 'pow'

class Genesis():
    '''
    @brief Genesis manage class
    '''
    __genesisPoA = '''{
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

    __genesisPoW = '''{
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
    
    def __init__(self, consensus:ConsensusMechanism) -> None:
        self.__consensusMechaism = consensus
        self.__genesis = json.loads(self.__genesisPoA) if self.__consensusMechaism == ConsensusMechanism.POA else json.loads(self.__genesisPoW)
    
    def allocateBalance(self, accounts:List[EthAccount]) -> Genesis:
        '''
        @brief allocate balance to account on genesis. It will update the genesis file
        '''
        for account in accounts:
            self.__allocateBalance(account.address,account.alloc_balance)
        return self

    def setSealer(self, accounts:List[EthAccount]) -> Genesis:
        if len(accounts) > 0: self.__replaceExtraData(self.__generateGenesisExtraData(accounts))
        return self

    def __generateGenesisExtraData(self, prefunded_accounts: List[EthAccount]) -> str:
        '''
        @brief Clique extradata field, used to define PoA validators/sealers must match the following format:
        First part: 32bytes vanity, meaning whatever you want here since it’s expressed as an hex string (64 chars long as one byte is 2 chars), using puppeth tool, it's filled with 0s.
        Second part: concatenated list of sealers/validators nodes addresses. Each address written as hex string without the “0x” prefix and must be 20 bytes long (40 chars long as one byte is 2 chars).
        Third part: a 65 bytes signature suffix called proposer seal. It’s used to identify the proposer of the new validator in a block. Given we talk here about the genesis file, this seal has no reason to be because no specific node proposed it, it’s the base on which everyone agree before starting. So it must be filled with zeros (65 zeros). Puppeth tool puts 130 0s.
        
        @returns the fully generated extraData field for the genesis
        '''
        extraData = "0x" + "0" * 64
        for account in prefunded_accounts:
            extraData = extraData + account.address[2:]
        
        return extraData + "0" * 130
    
    def __allocateBalance(self, address:str, balance:str) -> None:
        self.__genesis["alloc"][address[2:]] = {"balance":"{}".format(balance)}
        
    def __replaceExtraData(self, content:str) -> None:
        self.__genesis["extraData"] = content

    def __str__(self) -> str:
        return json.dumps(self.__genesis)

    def __repr__(self) -> str:
        return json.dumps(self.__genesis)

class EthAccount():
    """
    @brief Ethereum Local Account.
    """

    address: str    # account address
    keystore_content: str   # the content of keystore file
    keystore_filename:str   # the name of keystore file 
    alloc_balance: int

    def __init__(self, alloc_balance:int = 0,password:str = "admin", keyfile: str = None) -> None:
        """
        @brief create a Ethereum Local Account when initialize

        @param alloc_balance the balance need to be alloc
        @param password encrypt password for creating new account, decrypt password for importing account
        @param keyfile content of the keystore file. If this parameter is None, this function will create a new account, if not, it will import account from keyfile
        """
        from eth_account import Account
        self.lib_eth_account = Account
        self.account = self.__importAccout(keyfile=keyfile, password=password) if keyfile else self.__createAccount()
        self.address = self.account.address
        self.__validate_balance(alloc_balance=alloc_balance)
        self.alloc_balance = alloc_balance
        # encrypt private for Ethereum Client, like geth and generate the content of keystore file
        encrypted = self.lib_eth_account.encrypt(self.account.key, password=password)
        self.keystore_content = json.dumps(encrypted)
        # generate the name of the keyfile
        datastr = datetime.now(timezone.utc).isoformat().replace("+00:00", "000Z").replace(":","-")
        self.keystore_filename = "UTC--"+datastr+"--"+encrypted["address"]

    def __validate_balance(self, alloc_balance:int):
        """
        validate balance
        It only allow positive decimal integer
        """
        assert alloc_balance>=0 , "Invalid Balance Range: {}".format(alloc_balance)
    
    def __importAccout(self, keyfile: str, password = "admin"):
        """
        @brief import account from keyfile
        """
        print("importing account...")
        return self.lib_eth_account.from_key(self.lib_eth_account.decrypt(keyfile_json=keyfile,password=password))
    
    def __createAccount(self):
        """
        @brief create account
        """
        print("creating account...")
        return  self.lib_eth_account.create()


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
    __prefunded_accounts: List[EthAccount]
    __consensus_mechanism: ConsensusMechanism
    __geth_binary: str
    __geth_client: str

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
        self.__prefunded_accounts = [EthAccount(alloc_balance=32 * pow(10, 18), password="admin")] #create a prefunded account by default. It ensure POA network works when create/import prefunded account is not called.
        self.__consensus_mechanism = None # keep as empty to make sure the OR statement works in the install function
        self.__geth_binary = ""

    def __createNewAccountCommand(self, node: Node):
        if self.__create_new_account > 0:
            """!
            @brief generates a shell command which creates a new account in ethereum network.
    
            @param ethereum node on which we want to deploy the changes.
            
            """
            command = " sleep 20\n\
            {} --password /tmp/eth-password account new \n\
            ".format(self.__geth_client)

            for count in range(self.__create_new_account):
                node.appendStartCommand('(\n {})&'.format(command))

    def __unlockAccountsCommand(self, node: Node):
        if self.__unlockAccounts:
            """!
            @brief automatically unlocking the accounts in a node.
            Currently used to automatically be able to use our emulator using Remix.
            """

            base_command = "sleep 20\n\
            {} --exec 'personal.unlockAccount(eth.accounts[{}],\"admin\",0)' attach\n\
            "
            
            full_command = ""
            for i in range(self.__create_new_account + 1):
                full_command += base_command.format(self.__geth_client, str(i))

            node.appendStartCommand('(\n {})&'.format(full_command))

    def __addMinerStartCommand(self, node: Node):
        if self.__start_Miner_node:
            """!
            @brief generates a shell command which start miner as soon as it the miner is booted up.
            
            @param ethereum node on which we want to deploy the changes.
            
            """   
            command = " sleep 20\n\
            {} --exec 'eth.defaultAccount = eth.accounts[0]' attach \n\
            {} --exec 'miner.start(1)' attach \n\
            ".format(self.__geth_client, self.__geth_client)
            node.appendStartCommand('(\n {})&'.format(command))

    def __deploySmartContractCommand(self, node: Node):
        if self.__smart_contract != None :
            smartContractCommand = self.__smart_contract.generateSmartContractCommand()
            node.appendStartCommand('(\n {})&'.format(smartContractCommand))
    
    def __updateGenesis(self, genesis: Genesis, prefunded_accounts:List[EthAccount]) -> Genesis:
        genesis.allocateBalance(prefunded_accounts)
        genesis.setSealer(prefunded_accounts)
        return genesis

    def __saveAccountKeystoreFile(self, account: EthAccount, saveDirectory: str):
        saveDirectory = saveDirectory+'/{}/'.format(self.__id)
        os.makedirs(saveDirectory, exist_ok=True)
        f = open(saveDirectory+account.keystore_filename, "w")
        f.write(account.keystore_content)
        f.close()
    
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
        node_specific_prefunded_accounts = self.getPrefundedAccounts()
        if len(node_specific_prefunded_accounts) > 0:
            for account in node_specific_prefunded_accounts:
                node.appendFile("/tmp/keystore/"+account.keystore_filename, account.keystore_content)
      
        # We can specify nodes to use a consensus different from the base one
        consensus = self.getConsensusMechanism() or eth.getBaseConsensusMechanism() 
        genesis = Genesis(consensus=consensus)

        # update genesis.json
        genesis = self.__updateGenesis(genesis, eth.getAllPrefundedAccounts())
    
        node.appendFile('/tmp/eth-genesis.json', str(genesis))
        node.appendFile('/tmp/eth-nodes', '\n'.join(eth.getBootNodes()[:]))
        node.appendFile('/tmp/eth-bootstrapper', ETHServerFileTemplates['bootstrapper'])
        node.appendFile('/tmp/eth-password', 'admin') 

        node.addSoftware('software-properties-common')
        # tap the eth repo
        node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')  
        # install geth and bootnode
        install_command = 'apt-get update && apt-get install --yes bootnode {}' 
        #node.addBuildCommand('apt-get update && apt-get install --yes geth bootnode')
       
       
        geth_client = "geth"
        if self.getLocalGethBinary():
            geth_client = "bash -c /root/.ethereum/{}".format(self.__geth_binary)
            node.addBuildCommand(install_command.format(''))
        else:
            node.addBuildCommand(install_command.format(geth_client))
        
        self.__geth_client = geth_client
        # set the data directory
        datadir_option = "--datadir /root/.ethereum"

        # genesis
        node.appendStartCommand('[ ! -e "/root/.ethereum/geth/nodekey" ] && {} {} init /tmp/eth-genesis.json'.format(geth_client,datadir_option))

        # create account via pre-defined password
        node.appendStartCommand('[ -z `ls -A /root/.ethereum/keystore` ] && {} {} --password /tmp/eth-password account new'.format(geth_client, datadir_option)) 
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
        common_flags = '{} --identity="NODE_{}" --networkid=10 --syncmode full --verbosity=2 --allow-insecure-unlock --port {} --http --http.addr 0.0.0.0 --http.port {}'.format(datadir_option, self.__id, base_port,  self.getGethHttpPort())
        
        # Flags updated to accept external connections
        if self.externalConnectionEnabled():
            apis = "web3,eth,debug,personal,net,clique"
            http_whitelist_domains = "*"
            ws_whitelist_domains = "*"
            whitelist_flags = "--http.corsdomain \"{}\" --http.api {} --ws --ws.addr 0.0.0.0 --ws.port {} --ws.api {} --ws.origins \"{}\" ".format(http_whitelist_domains, apis, 8546, apis, ws_whitelist_domains)
            common_flags = '{} {}'.format(common_flags, whitelist_flags)
        
        if not self.isDiscoverable():
            common_flags = '{} {}'.format(common_flags, "--nodiscover")

        # Base geth command
        geth_command = 'nice -n 19 {} {}'.format(geth_client, common_flags)
        
        # Manual vs automated geth command execution
        # In the manual approach, the geth command is only thrown in a file in /tmp/run.sh
        # In the automated approach, the /tmp/run.sh file is executed by the start.sh (Virtual node) 
        
        # Echoing the geth command to /tmp/run.sh in each container
        node.appendStartCommand('echo \'{} --bootnodes "$(cat /tmp/eth-node-urls)"\' > /tmp/run.sh'.format(geth_command), True) 
       
        # Making run.sh executable
        node.appendStartCommand('sleep 10')
        node.appendStartCommand('chmod +x /tmp/run.sh')
        
        # moving keystore to the proper folder
        for account in self.getPrefundedAccounts():
            node.appendStartCommand("cp /tmp/keystore/{} /root/.ethereum/keystore/".format(account.keystore_filename),True)

        # Adding /tmp/run.sh in start.sh file to automate them
        if not(eth.isManual()):
            node.appendStartCommand('/tmp/run.sh &')

            self.__createNewAccountCommand(node)
            self.__unlockAccountsCommand(node)
            self.__addMinerStartCommand(node)
            self.__deploySmartContractCommand(node)

    def useLocalGethBinary(self, executable:str) -> EthereumServer:
        """
        @brief setting the filename of modified geth binary
        """
        self.__geth_binary = executable

        return self

    def getLocalGethBinary(self) -> str:
        """
        @brief getting the binary name
        """
        return self.__geth_binary

    def setNoDiscover(self) -> EthereumServer:
        """
        @brief setting the --nodiscover geth flag
        """
        self.__is_discoverable = False
        return self

    def isDiscoverable(self) -> str:
        """
        @brief making sure nodes can automatically discover their peers
        """
        return self.__is_discoverable

    def setConsensusMechanism(self, consensus:ConsensusMechanism=ConsensusMechanism.POA) -> EthereumServer:
        '''
        @brief We can have more than one consensus mechanism at the same time
        The base consensus (poa) applies to all of the nodes by default except if this API is called
        We can set a different consensus for the nodes of our choice
        '''
        self.__consensus_mechanism = consensus
        
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
    
    def createPrefundedAccounts(self, balance: int = 0, number: int = 1, password: str = "admin", saveDirectory:str = None) -> EthereumServer:
        """
        @brief Call this api to create new prefunded account with balance

        @param number the number of prefunded account need to create
        @param balance the balance need to be allocated to the prefunded accounts
        @param password the password of account for the Ethereum client

        @returns self
        """
        for _ in range(number):    
            account = EthAccount(alloc_balance=balance,password=password)
            if saveDirectory:
                self.__saveAccountKeystoreFile(account=account, saveDirectory=saveDirectory)
            self.__prefunded_accounts.append(account)
        return self
    
    def importPrefundedAccount(self, keyfileDirectory:str, password:str = "admin", balance: int = 0) -> EthereumServer:
        f = open(keyfileDirectory, "r")
        keystoreFileContent = f.read()
        account = EthAccount(alloc_balance=balance, password=password,keyfile=keystoreFileContent)
        self.__prefunded_accounts.append(account)
        return self
    
    def getPrefundedAccounts(self) -> List[EthAccount]:
        """
        @brief Call this api to get the prefunded accounts for this node
        """

        return self.__prefunded_accounts

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
    __joined_prefunded_accounts: List[EthAccount]

    __save_state: bool
    __save_path: str
    
    __manual_execution: bool
    __base_consensus_mechanism: ConsensusMechanism

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
        self.__joined_prefunded_accounts = []

        self.__save_state = saveState
        self.__save_path = statePath

        self.__manual_execution = manual
        self.__base_consensus_mechanism = ConsensusMechanism.POW # set by default in case the API is not used

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
    
    def getAllPrefundedAccounts(self) -> List[EthAccount]:
        """
        @brief Get a joined list of all the created prefunded accounts on all nodes
        
        @returns list of EthAccount
        """
        return self.__joined_prefunded_accounts

    def setBaseConsensusMechanism(self, mechanism:ConsensusMechanism = ConsensusMechanism.POA) -> bool:
        """
        @brief select a consensus mechanism for the blockchain network. Default is Proof of authority

        @returns bool
        """
        self.__base_consensus_mechanism = mechanism
        return True

    def getBaseConsensusMechanism(self) -> ConsensusMechanism:
        """
        @returns the consensus mechanism for the current network
        """
        return self.__base_consensus_mechanism

    def _doConfigure(self, node: Node, server: EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())

        if server.isBootNode():
            self._log('adding as{}/{} as bootnode...'.format(node.getAsn(), node.getName()))
            self.__boot_node_addresses.append(addr)

        if len(server.getPrefundedAccounts()) > 0:
            self.__joined_prefunded_accounts.extend(server.getPrefundedAccounts())

        if self.__save_state:
            node.addSharedFolder('/root/.ethereum', '{}/{}'.format(self.__save_path, server.getId()))
    
    def install(self, vnode: str) -> EthereumServer:
        """!
        @brief Override function of Sevice.install
        Here is downcasting the return for IntelliSense :)
        """
        return super().install(vnode)

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
