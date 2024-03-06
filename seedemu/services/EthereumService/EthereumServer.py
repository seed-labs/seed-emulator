from __future__ import annotations
from seedemu.core import Node, Server, BaseSystem
from .EthEnum import *
from .EthUtil import *
from typing import List
from seedemu.services.EthereumService import *
from .EthTemplates import EthServerFileTemplates, GethCommandTemplates
from .EthTemplates.LighthouseCommandTemplates import *

ETH_LABEL_META = 'ethereum.{key}'

class EthereumServer(Server):
    """!
    @brief The Ethereum Server
    """

    _id: int
    _blockchain: Blockchain
    _is_bootnode: bool
    _bootnode_http_port: int
    _smart_contract: SmartContract
    _accounts: List[AccountStructure]
    _mnemonic_accounts: List[AccountStructure]
    _consensus_mechanism: ConsensusMechanism

    _custom_geth_binary_path: str
    _custom_geth_command_option: str
    _geth_options: dict

    _data_dir: str
    _syncmode: Syncmode
    _snapshot: bool
    _no_discover: bool 
    _enable_http: bool
    _geth_http_port: int
    _enable_ws: bool
    _geth_ws_port: int
    _unlock_accounts: bool
    _start_mine: bool
    _miner_thread: int
    _coinbase: str
    
    _geth_start_command: str

    _role: list

    def __init__(self, id: int, blockchain:Blockchain):
        """!
        @brief create new eth server.
        @param id serial number of this server.
        """

        super().__init__()

        self._id = id
        self._blockchain = blockchain
        self._is_bootnode = False
        self._bootnode_http_port = 8088
        self._smart_contract = None
        self._accounts = []
        self._mnemonic, self._account_base_balance, self._account_total = self._blockchain.getEmuAccountParameters()
        self._mnemonic_accounts = EthAccount.createEmulatorAccountsFromMnemonic(self._id, mnemonic=self._mnemonic, balance=self._account_base_balance, total=self._account_total, password="admin")
        self._consensus_mechanism = blockchain.getConsensusMechanism()

        self._custom_geth_binary_path = None
        self._custom_geth_command_option = None
        self._geth_options = {"finding_peers": "", "http":"", "ws":"", "pos":"", "custom":"", "unlock":"", "mine":""}

        self._data_dir = "/root/.ethereum"
        self._syncmode = Syncmode.FULL
        self._snapshot = False
        self._no_discover = False
        self._enable_ws = False
        self._enable_http = False
        self._geth_http_port = 8545
        self._geth_ws_port = 8546
        self._unlock_accounts = True
        self._start_mine = False
        self._miner_thread = 1
        self._coinbase = None
        self._geth_start_command = ""

        self._base_system = BaseSystem.SEEDEMU_ETHEREUM

        self._role = []
        

    def _generateGethStartCommand(self):
        """!
        @brief generate geth start commands from the properties. 

        @returns geth command. 
        """
        if self._no_discover:
            self._geth_options['finding_peers'] = GethCommandTemplates['nodiscover']
        else:
            self._geth_options['finding_peers'] = GethCommandTemplates['bootnodes']
        if self._enable_http:
            self._geth_options['http'] = GethCommandTemplates['http'].format(gethHttpPort=self._geth_http_port)
        if self._enable_ws:
            self._geth_options['ws'] = GethCommandTemplates['ws'].format(gethWsPort=self._geth_ws_port)
        if self._custom_geth_command_option:
            self._geth_options['custom'] = self._custom_geth_command_option
        if self._unlock_accounts:
            accounts = []
            for account in self._accounts:
                accounts.append(account.address)
            self._geth_options['unlock'] = GethCommandTemplates['unlock'].format(accounts=', '.join(accounts))
        self._geth_start_command = GethCommandTemplates['base'].format(node_id=self._id, chain_id=self._blockchain.getChainId(), datadir=self._data_dir, syncmode=self._syncmode.value, snapshot=self._snapshot, option=self._geth_options)
        
    def install(self, node: Node, eth: EthereumService):
        """!
        @brief ETH server installation step.
        
        @param node node object
        @param eth reference to the eth service.
        @param allBootnode all-bootnode mode: all nodes are boot node.
        
        """

        node.appendClassName('EthereumService')
        node.setLabel(ETH_LABEL_META.format(key='node_id'), self.getId())
        node.setLabel(ETH_LABEL_META.format(key='consensus'), self._consensus_mechanism.value)
        node.setLabel(ETH_LABEL_META.format(key='chain_name'), self._blockchain.getChainName())
        node.setLabel(ETH_LABEL_META.format(key='chain_id'), self._blockchain.getChainId())
        
        if self.isBootNode(): self._role.append("bootnode")
        if self.isStartMiner(): self._role.append("miner")
        node.setLabel(ETH_LABEL_META.format(key='role'), json.dumps(self._role).replace("\"", "\\\""))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has no interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        self.__genesis = self._blockchain.getGenesis()

        node.setFile('/tmp/eth-genesis.json', self.__genesis.getGenesis())
    
        # set account passwords to /tmp/eth-password
        account_passwords = []

        for account in self._accounts:
            node.setFile("/tmp/keystore/"+account.keystore_filename, account.keystore_content)
            account_passwords.append(account.password)

        node.setFile('/tmp/eth-password', '\n'.join(account_passwords))

        # install required software
        # node.addSoftware('software-properties-common')
        # tap the eth repo
        # node.addBuildCommand('add-apt-repository ppa:ethereum/ethereum')

        # install geth and bootnode
        if self._custom_geth_binary_path : 
            #node.addBuildCommand('apt-get update && apt-get install --yes bootnode')
            node.importFile("../../"+self._custom_geth_binary_path, '/usr/bin/geth')
            node.appendStartCommand("chmod +x /usr/bin/geth")
        # else:
        #     node.addBuildCommand('apt-get update && apt-get install --yes geth bootnode')

        # genesis
        node.appendStartCommand('[ ! -e "/root/.ethereum/geth/nodekey" ] && geth --datadir {} init /tmp/eth-genesis.json'.format(self._data_dir))
        
        # copy keystore to the proper folder
        for account in self._accounts:
            node.appendStartCommand("cp /tmp/keystore/{} /root/.ethereum/keystore/".format(account.keystore_filename))

        if self._is_bootnode:
            # generate enode url. other nodes will access this to bootstrap the network.
            node.appendStartCommand('[ ! -e "/root/.ethereum/geth/bootkey" ] && bootnode -genkey /root/.ethereum/geth/bootkey')
            node.appendStartCommand('echo "enode://$(bootnode -nodekey /root/.ethereum/geth/bootkey -writeaddress)@{}:30301" > /tmp/eth-enode-url'.format(addr))
            
            # Default port is 30301, use -addr :<port> to specify a custom port
            node.appendStartCommand('bootnode -nodekey /root/.ethereum/geth/bootkey -verbosity 9 -addr {}:30301 2> /tmp/bootnode-logs &'.format(addr))          
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self._bootnode_http_port), True)

        # get other nodes IP for the bootstrapper.
        bootnodes = self._blockchain.getBootNodes()[:]
        if len(bootnodes) > 0 :
            node.setFile('/tmp/eth-nodes', '\n'.join(bootnodes))
            
            node.setFile('/tmp/eth-bootstrapper', EthServerFileTemplates['bootstrapper'])

            # load enode urls from other nodes
            node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
            node.appendStartCommand('/tmp/eth-bootstrapper')

        # launch Ethereum process.
        node.appendStartCommand(self._geth_start_command, True) 
        

        # Rarely used and tentatively not supported. 
        # if self.__smart_contract != None :
        #     smartContractCommand = self.__smart_contract.generateSmartContractCommand()
        #     node.appendStartCommand('(\n {})&'.format(smartContractCommand))

    def setCustomGeth(self, customGethBinaryPath:str) -> EthereumServer:
        """
        @brief set custom geth binary file

        @param customGethBinaryPath set absolute path of geth binary to move to the service.

        @returns self, for chaining API calls.
        """
        assert path.exists(customGethBinaryPath), "EthereumServer::setCustomGeth: custom geth binary file does not exist. path : {}".format(customGethBinaryPath)

        self._custom_geth_binary_path = customGethBinaryPath

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

        self._custom_geth_command_option = customOptions
        return self
        
    def setSyncmode(self, syncmode:Syncmode) -> EthereumServer:
        """
        @brief setting geth syncmode (default: snap)
        
        @param syncmode use Syncmode enum options.
                Syncmode.SNAP, Syncmode.FULL, Syncmode.LIGHT

        @returns self, for chaining API calls.
        """
        self._syncmode = syncmode
        return self

    def setNoDiscover(self, noDiscover:bool = True) -> EthereumServer:
        """
        @brief setting the automatic peer discovery to true/false
        """
        self._no_discover = noDiscover
        return self

    def setSnapshot(self, snapshot:bool = True) -> EthereumServer:
        """!
        @brief set geth snapshot 
        
        @param snapshot bool

        @returns self, for chaining API calls.
        """
        self._snapshot = snapshot
        return self

    def getId(self) -> int:
        """!
        @brief get ID of this node.
        @returns ID.
        """
        return self._id

    def setBootNode(self, isBootNode: bool) -> EthereumServer:
        """!
        @brief set bootnode status of this node.
        Note: if no nodes are configured as boot nodes, all nodes will be each
        other's boot nodes.
        @param isBootNode True to set this node as a bootnode, False otherwise.
        
        @returns self, for chaining API calls.
        """
        self._is_bootnode = isBootNode

        return self

    def isBootNode(self) -> bool:
        """!
        @brief get bootnode status of this node.
        @returns True if this node is a boot node. False otherwise.
        """
        return self._is_bootnode

    def setBootNodeHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number hosting the enode url file.
        @param port port
        @returns self, for chaining API calls.
        """

        self._bootnode_http_port = port

        return self


    def getBootNodeHttpPort(self) -> int:
        """!
        @brief get the http server port number hosting the enode url file.
        @returns port
        """

        return self._bootnode_http_port

    def setGethHttpPort(self, port: int) -> EthereumServer:
        """!
        @brief set the http server port number for normal ethereum nodes
        @param port port
        @returns self, for chaining API calls
        """
        
        self._geth_http_port = port
        
        return self

    def getGethHttpPort(self) -> int:
        """!
        @brief get the http server port number for normal ethereum nodes
        @returns int
        """
                
        return self._geth_http_port

    def setGethWsPort(self, port: int) -> EthereumServer:
        """!
        @brief set the ws server port number for normal ethereum nodes

        @param port port

        @returns self, for chaining API calls
        """
        
        self._geth_ws_port = port
        
        return self

    def getGethWsPort(self) -> int:
        """!
        @brief get the ws server port number for normal ethereum nodes

        @returns int
        """
                
        return self._geth_ws_port

    def enableGethHttp(self) -> EthereumServer:
        """!
        @brief setting a geth to enable http connection 
        """
        self._enable_http = True

        return self

    def isGethHttpEnabled(self) -> bool:
        """!
        @brief returns whether a geth enabled http connection or not
        """
        return self._enable_http

    def enableGethWs(self) -> EthereumServer:
        """!
        @brief setting a geth to enable ws connection
        """
        self._enable_ws = True

        return self

    def isGethWsEnabled(self) -> bool:
        """!
        @brief returns whether a geth enabled ws connection or not
        """

        return self._enable_ws

    def createAccount(self, balance:int, unit:EthUnit=EthUnit.ETHER, password="admin") -> EthereumServer:
        """
        @brief call this api to create new accounts

        @param balance the balance to be allocated to the account.
        @param unit EthUnit (Default: EthUnit.Ether)

        @returns self, for chaining API calls.

        """

        balance = balance * unit.value
        self._mnemonic_accounts.append(EthAccount.createEmulatorAccountFromMnemonic(self._id, mnemonic=self._mnemonic, balance=balance, index=self._account_total, password=password))
        self._account_total += 1
        return self

    # it should depend on createAccount() method
    def createAccounts(self, total:int, balance:int, unit:EthUnit=EthUnit.ETHER, password="admin") -> EthereumServer:
        """
        @brief Call this api to create new accounts.

        @param total The total number of account need to create.
        @param balance The balance to allocate to the accounts.
        @param unit The unit of Ethereum. EthUnit (Default: EthUnit.Ether).

        @returns self, for chaining API calls.
        """

        for i in range(total):
            self.createAccount(balance, unit, password)

        return self

    def _createAccounts(self, eth:EthereumService) -> EthereumServer:
        """
        @brief Call this api to create new accounts from account_info

        @returns self, for chaining API calls.
        """
        self._accounts.extend(self._mnemonic_accounts)

        return self    
    
    def importAccount(self, keyfilePath:str, password:str = "admin", balance: int = 0, unit:EthUnit=EthUnit.ETHER) -> EthereumServer:
        """
        @brief Call this api to import an account.

        @param keyfilePath The keyfile path to import.
        @param password The password to decrypt the keyfile.
        @param balance The balance to allocate to the account.

        @returns self, for chaining API calls.
        """

        assert path.exists(keyfilePath), "EthereumServer::importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        account = EthAccount.importAccount(balance=balance,password=password, keyfilePath=keyfilePath)
        self._accounts.append(account)
        return self
    

    def _getAccounts(self) -> List[AccountStructure]:
        """
        @brief Call this api to get the accounts for this node
        
        @returns accounts
        """

        return self._accounts
        

    def unlockAccounts(self) -> EthereumServer:
        """!
        @brief This is mainly used to unlock the accounts in the remix node to make it directly possible for transactions to be 
        executed through Remix without the need to access the geth account in the docker container and unlocking manually

        @returns self, for chaining API calls.
        """
        self._unlock_accounts = True

        return self
        
    def startMiner(self) -> EthereumServer:
        """!
        @brief Call this api to start Miner in the node.

        @returns self, for chaining API calls.
        """
        self._start_mine = True
        self._syncmode = Syncmode.FULL

        return self

    def isStartMiner(self) -> bool:
        """!
        @brief Call this api to get startMiner status in the node.
        
        @returns __start_mine status.
        """
        return self._start_mine

    def deploySmartContract(self, smart_contract: SmartContract) -> EthereumServer:
        """!
        @brief Call this api to deploy smartContract on the node.
        @returns self, for chaining API calls.
        """
        self._smart_contract = smart_contract

        return self

    def getBlockchain(self):
        return self._blockchain


class PoAServer(EthereumServer):
    def __init__(self, id: int, blockchain: Blockchain):
        """!
        @brief Create new eth server.

        @param id The serial number of this server.
        """

        super().__init__(id, blockchain)
        
    def _generateGethStartCommand(self):
        if self._start_mine:
            assert len(self._accounts) > 0, 'EthereumServer::__generateGethStartCommand: To start mine, ethereum server need at least one account.'
            assert self._unlock_accounts, 'EthereumServer::__generateGethStartCommand: To start mine in POA(clique), accounts should be unlocked first.'
            if self._coinbase:
                coinbase = self._coinbase
            else:
                coinbase = self._accounts[0].address
            self._geth_options['mine'] = GethCommandTemplates['mine'].format(coinbase=coinbase, num_of_threads=self._miner_thread)
        super()._generateGethStartCommand()
        

class PoWServer(EthereumServer):
    def __init__(self, id:int, blockchain:Blockchain):
        """!
        @brief Create new eth server.

        @param id The serial number of this server.
        """

        super().__init__(id, blockchain)
    
    def _generateGethStartCommand(self):
        super()._generateGethStartCommand()

        self._geth_start_command = "nice -n 19 " + self._geth_start_command
        if self._start_mine:
            if self._coinbase:
                coinbase = self._coinbase
            else:
                coinbase = self._accounts[0].address
            assert len(self._accounts) > 0, 'EthereumServer::__generateGethStartCommand: To start mine, ethereum server need at least one account.'
            self._geth_start_command += GethCommandTemplates['mine'].format(coinbase=coinbase, num_of_threads=self._miner_thread)
        
class PoSServer(PoAServer):
    __terminal_total_difficulty: int
    __is_beacon_setup_node: bool
    __beacon_setup_http_port: int
    __beacon_peer_counts:int

    def __init__(self, id: int, blockchain:Blockchain):
        """!
        @brief Create new eth server.

        @param id Serial number of this server.
        """

        super().__init__(id, blockchain)

        self.__is_beacon_setup_node = False
        self.__beacon_setup_http_port = 8090
        self.__terminal_total_difficulty = self._blockchain.getTerminalTotalDifficulty()
        self.__is_beacon_validator_at_genesis = False
        self.__is_beacon_validator_at_running = False
        self.__is_manual_deposit_for_validator = False
        self.__beacon_peer_counts = 5

    def _generateGethStartCommand(self):
        self._geth_options['pos'] = GethCommandTemplates['pos'].format(difficulty=self.__terminal_total_difficulty)
        super()._generateGethStartCommand()
        
    def __install_beacon(self, node:Node, eth:EthereumService):
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has no interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        beacon_setup_node = self._blockchain.getBeaconSetupNodeIp()

        assert beacon_setup_node != "", 'EthereumServer::install: Ethereum Service has no beacon_setup_node.'

        bootnode_start_command = ""
        bc_start_command = LIGHTHOUSE_BN_CMD.format(eth_id=self.getId(),ip_address=addr, target_peers=self.__beacon_peer_counts)
        vc_start_command = ""
        wallet_create_command = ""
        validator_create_command = ""
        validator_deposit_sh = ""
        if self._is_bootnode:
            bootnode_start_command = LIGHTHOUSE_BOOTNODE_CMD.format(ip_address=addr)
        if self.__is_beacon_validator_at_running:
            node.setFile('/tmp/seed.pass', 'seedseedseed')
            wallet_create_command = LIGHTHOUSE_WALLET_CREATE_CMD.format(eth_id=self.getId())
            validator_create_command = LIGHTHOUSE_VALIDATOR_CREATE_CMD.format(eth_id=self.getId()) 
            node.setFile('/tmp/deposit.sh', VALIDATOR_DEPOSIT_SH.format(eth_id=self.getId()))
            node.appendStartCommand('chmod +x /tmp/deposit.sh')
            if not self.__is_manual_deposit_for_validator:
                validator_deposit_sh = "/tmp/deposit.sh"
        if self.__is_beacon_validator_at_genesis or self.__is_beacon_validator_at_running:
            vc_start_command = LIGHTHOUSE_VC_CMD.format(eth_id=self.getId(), ip_address=addr, acct_address=self._accounts[0].address)
            
        node.setFile('/tmp/beacon-setup-node', beacon_setup_node)
        node.setFile('/tmp/beacon-bootstrapper', EthServerFileTemplates['beacon_bootstrapper'].format( 
                                is_validator="true" if self.__is_beacon_validator_at_genesis else "false",
                                is_bootnode="true" if self._is_bootnode else "false",
                                eth_id=self.getId(),
                                bootnode_start_command=bootnode_start_command,
                                bc_start_command=bc_start_command,
                                vc_start_command=vc_start_command,
                                wallet_create_command=wallet_create_command,
                                validator_create_command=validator_create_command,
                                validator_deposit_sh=validator_deposit_sh
                    ))
        node.setFile('/tmp/jwt.hex', '0xae7177335e3d4222160e08cecac0ace2cecce3dc3910baada14e26b11d2009fc')
        
        node.appendStartCommand('chmod +x /tmp/beacon-bootstrapper')
        node.appendStartCommand('/tmp/beacon-bootstrapper')

    def install(self, node: Node, eth: EthereumService):
        if self.__is_beacon_setup_node:
            beacon_setup_node = BeaconSetupServer(ttd=self.__terminal_total_difficulty)
            beacon_setup_node.install(node, self._blockchain)
            return 
        
        if self.__is_beacon_validator_at_genesis:
            self._role.append("validator_at_genesis")
        if self.__is_beacon_validator_at_running:
            self._role.append("validator_at_running")
        
        super().install(node,eth)
        self.__install_beacon(node, eth)

    def enablePOSValidatorAtGenesis(self):
        self.__is_beacon_validator_at_genesis = True
        return self

    def isValidatorAtGenesis(self):
        return self.__is_beacon_validator_at_genesis

    def isValidatorAtRunning(self):
        return self.__is_beacon_validator_at_running

    def enablePOSValidatorAtRunning(self, is_manual:bool=False):
        self.__is_beacon_validator_at_running = True
        self.__is_manual_deposit_for_validator = is_manual
        return self

    def isBeaconSetupNode(self):
        return self.__is_beacon_setup_node

    def setBeaconSetupNode(self, port=8090):
        self.__is_beacon_setup_node = True
        self.__beacon_setup_http_port = port
        return self

    def getBeaconSetupNodeIp(self):
        return self.__beacon_setup_node_ip

    # def setBaseAccountBalance(self, balance:int):
    #     self._accounts_info[0] = (balance, "admin", None)
    #     return self

    def setBeaconPeerCounts(self, peer_counts:int):
        self.__beacon_peer_counts = peer_counts
        return self
    
    def getBeaconSetupHttpPort(self) -> int:
        return self.__beacon_setup_http_port

    def setBeaconSetupHttpPort(self, port:int):
        self.__beacon_setup_http_port = port
        return self
class BeaconSetupServer():

    """!
    @brief The WebServer class.
    """

    BEACON_GENESIS = '''\
CONFIG_NAME: mainnet
PRESET_BASE: mainnet
TERMINAL_TOTAL_DIFFICULTY: "{terminal_total_difficulty}"
TERMINAL_BLOCK_HASH: "0x0000000000000000000000000000000000000000000000000000000000000000"
TERMINAL_BLOCK_HASH_ACTIVATION_EPOCH: "18446744073709551615"
SAFE_SLOTS_TO_IMPORT_OPTIMISTICALLY: "128"
MIN_GENESIS_ACTIVE_VALIDATOR_COUNT: "1"
GENESIS_FORK_VERSION: "0x42424242"
GENESIS_DELAY: "0"
ALTAIR_FORK_VERSION: "0x01000000"
ALTAIR_FORK_EPOCH: "0"
BELLATRIX_FORK_VERSION: "0x02000000"
BELLATRIX_FORK_EPOCH: "0"
SECONDS_PER_SLOT: "12"
SECONDS_PER_ETH1_BLOCK: "14"
MIN_VALIDATOR_WITHDRAWABILITY_DELAY: "256"
SHARD_COMMITTEE_PERIOD: "256"
ETH1_FOLLOW_DISTANCE: "16"
INACTIVITY_SCORE_BIAS: "4"
INACTIVITY_SCORE_RECOVERY_RATE: "16"
EJECTION_BALANCE: "16000000000"
MIN_PER_EPOCH_CHURN_LIMIT: "4"
CHURN_LIMIT_QUOTIENT: "32"
PROPOSER_SCORE_BOOST: "40"
DEPOSIT_CHAIN_ID: "{chain_id}"
DEPOSIT_NETWORK_ID: "{chain_id}"
NETWORK_ID: "{chain_id}"
MAX_COMMITTEES_PER_SLOT: "10"
INACTIVITY_PENALTY_QUOTIENT_BELLATRIX: "8"
TARGET_COMMITTEE_SIZE: "{target_committee_size}"
TARGET_AGGREGATORS_PER_COMMITTEE: "{target_aggregator_per_committee}"
'''

    BEACON_BOOTNODE_HTTP_SERVER = '''\
from http.server import HTTPServer, BaseHTTPRequestHandler

eth_id = 0

class SeedHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = open("/local-testnet/{{}}.tar.gz".format(self.path), "rb")
        self.wfile.write(response.read())
        response.close()

httpd = HTTPServer(('0.0.0.0', {beacon_bootnode_http_port}), SeedHTTPRequestHandler)
httpd.serve_forever()
'''

    PREPARE_RESOURCE_TO_SEND = '''\
#!/bin/bash
let i=0
while read -r ethId; do {
    let i++
    mv /local-testnet/node_$i /local-testnet/eth-$ethId
    tar -czvf /local-testnet/eth-$ethId.tar.gz /local-testnet/eth-$ethId
}; done < /tmp/validator-ids
tar -czvf /local-testnet/testnet.tar.gz /local-testnet/testnet
tar -czvf /local-testnet/bootnode.tar.gz /local-testnet/bootnode
'''

    DEPLOY_CONTRACT = '''\
until curl --http0.9 -sHf http://{geth_node_ip}:8545 > /dev/null; do {{
        echo "beacon-setup-node: geth node is not ready, waiting..."
        sleep 3
        let count++
        [ $count -gt 60 ] && {{
            echo "beacon-setup-node: geth node connection failed too many times, skipping."
            ok=false
            break
        }}
    }}; done

while true; do {{
    blockNumber=`curl --data '{{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}}' -H "Content-Type: application/json" -X POST http://{geth_node_ip}:8545 | jq -r '.result' | cut -d 'x' -f 2`
    echo "current blockNumber :" $(( 16#$blockNumber ))
    if [ $(( 16#$blockNumber )) -gt 5 ]
    then
            break
    fi
    sleep 3
}}; done

while true; do {{
    lcli deploy-deposit-contract --eth1-http http://{geth_node_ip}:8545 --confirmations 1 --validator-count {validator_count} > contract_address.txt
    CONTRACT_ADDRESS=`head -1 contract_address.txt | cut -d '"' -f 2`
    if [[ $CONTRACT_ADDRESS = 0x* ]]; then
        break
    fi
    echo "beacon-setup-node: Waiting for Validator Deposit..."
    sleep 10

}}; done
'''
    
    __beacon_setup_http_port: int

    def __init__(self, ttd:int, consensus:ConsensusMechanism = ConsensusMechanism.POA):
        """!
        @brief BeaconSetupServer constructor.
        """

        self.__beacon_setup_http_port = 8090
        self.__terminal_total_difficulty = ttd
        self.__consensus_mechanism = consensus

    def install(self, node: Node, blockchain: Blockchain):
        """!
        @brief Install the service.
        """
        
        validator_ids = blockchain.getValidatorIds()
        validator_counts = len(validator_ids)

        bootnode_ip = blockchain.getBootNodes()[0].split(":")[0]
        miner_ip = blockchain.getMinerNodes()[0]
        
        #node.addBuildCommand('apt-get update && apt-get install -y --no-install-recommends software-properties-common python3 python3-pip')
        #node.addBuildCommand('pip install web3')
        node.appendStartCommand('lcli generate-bootnode-enr --ip {} --udp-port 30305 --tcp-port 30305 --genesis-fork-version 0x42424242 --output-dir /local-testnet/bootnode'.format(bootnode_ip))
        node.setFile("/tmp/config.yaml", self.BEACON_GENESIS.format(terminal_total_difficulty=self.__terminal_total_difficulty, chain_id=blockchain.getChainId(), 
                                                                    target_committee_size=blockchain.getTargetCommitteeSize(), 
                                                                    target_aggregator_per_committee = blockchain.getTargetAggregatorPerCommittee()))
        node.setFile("/tmp/validator-ids", "\n".join(validator_ids))
        node.appendStartCommand('mkdir /local-testnet/testnet')
        node.appendStartCommand('bootnode_enr=`cat /local-testnet/bootnode/enr.dat`')
        node.appendStartCommand('echo "- $bootnode_enr" > /local-testnet/testnet/boot_enr.yaml')
        node.appendStartCommand('cp /tmp/config.yaml /local-testnet/testnet/config.yaml')
        node.appendStartCommand(self.DEPLOY_CONTRACT.format(geth_node_ip=miner_ip, validator_count = validator_counts))
        node.appendStartCommand('lcli insecure-validators --count {validator_count} --base-dir /local-testnet/ --node-count {validator_count}'.format(validator_count = validator_counts))
        node.appendStartCommand('GENESIS_TIME=`date +%s`')
        node.appendStartCommand('''CONTRACT_ADDRESS=`head -1 contract_address.txt | cut -d '"' -f 2`''')
        node.appendStartCommand('''echo 'DEPOSIT_CONTRACT_ADDRESS: "'$CONTRACT_ADDRESS'"' >> /local-testnet/testnet/config.yaml''')
        node.appendStartCommand('''echo 'MIN_GENESIS_TIME: "'$GENESIS_TIME'"' >> /local-testnet/testnet/config.yaml''')
        node.appendStartCommand('''echo '3' > /local-testnet/testnet/deploy_block.txt''')
        node.appendStartCommand('''lcli interop-genesis --spec mainnet --genesis-time $GENESIS_TIME --testnet-dir /local-testnet/testnet {validator_count}'''.format(validator_count = validator_counts))
        node.setFile("/tmp/prepare_resource.sh", self.PREPARE_RESOURCE_TO_SEND)
        node.appendStartCommand("chmod +x /tmp/prepare_resource.sh")
        node.appendStartCommand("/tmp/prepare_resource.sh")
        node.setFile('/local-testnet/beacon_bootnode_http_server.py', self.BEACON_BOOTNODE_HTTP_SERVER.format(beacon_bootnode_http_port=self.__beacon_setup_http_port))
        node.appendStartCommand('python3 /local-testnet/beacon_bootnode_http_server.py', True)

    def getBeaconSetupHttpPort(self) -> int:
        return self.__beacon_setup_http_port

    def setBeaconSetupHttpPort(self, port:int) -> BeaconSetupServer:
        self.__beacon_setup_http_port = port
        return self

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Beacon Setup server object.\n'

        return out
