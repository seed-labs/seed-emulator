from __future__ import annotations
from seedemu.core import Node, Server
from .EthEnum import *
from .EthUtil import *
from typing import Tuple, List
from seedemu.services import EthereumService
from .EthTemplates import EthServerFileTemplates, GethCommandTemplates
from .EthTemplates.LighthouseCommandTemplates import *

class EthereumServer(Server):
    """!
    @brief The Ethereum Server
    """

    __id: int
    __is_bootnode: bool
    __bootnode_http_port: int
    __beacon_peer_counts:int
    __smart_contract: SmartContract
    __accounts: List[EthAccount]
    __accounts_info: List[Tuple[int, str, str]]
    __consensus_mechanism: ConsensusMechanism

    __is_beacon_setup_node: bool
    __beacon_setup_http_port: int

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
    __terminal_total_difficulty: int
    

    def __init__(self, id: int):
        """!
        @brief create new eth server.
        @param id serial number of this server.
        """

        super().__init__()

        self.__id = id
        self.__is_bootnode = False
        self.__is_beacon_validator_at_genesis = False
        self.__is_beacon_validator_at_running = False
        self.__is_manual_deposit_for_validator = False
        self.__beacon_peer_counts = 5
        self.__beacon_validator_count = 100
        self.__bootnode_http_port = 8088
        self.__smart_contract = None
        self.__accounts = []
        self.__accounts_info = [(0, "admin", None)]
        self.__consensus_mechanism = ConsensusMechanism.POW
        self.__genesis = Genesis(self.__consensus_mechanism)

        self.__is_beacon_setup_node = False
        self.__beacon_setup_http_port = 8090

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
        self.__enable_pos = False
        self.__terminal_total_difficulty = 20

    def __generateGethStartCommand(self):
        """!
        @brief generate geth start commands from the properties. 

        @returns geth command. 
        """
        geth_start_command = GethCommandTemplates['base'].format(node_id=self.__id, datadir=self.__data_dir, syncmode=self.__syncmode.value, snapshot=self.__snapshot)

        if self.__consensus_mechanism == ConsensusMechanism.POW:
            geth_start_command = "nice -n 19 " + geth_start_command

        if self.__no_discover:
            geth_start_command += GethCommandTemplates['nodiscover']
        else:
            geth_start_command += GethCommandTemplates['bootnodes']
        if self.__enable_http:
            geth_start_command += GethCommandTemplates['http'].format(gethHttpPort=self.__geth_http_port)
        if self.__enable_ws:
            geth_start_command += GethCommandTemplates['ws'].format(gethWsPort=self.__geth_ws_port)
        if self.__enable_pos:
            geth_start_command += GethCommandTemplates['pos'].format(difficulty=self.__terminal_total_difficulty)
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
    
    def __install_beacon(self, node:Node, eth:EthereumService):
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has no interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        beacon_setup_node = eth.getBeaconSetupNodeIp()

        assert beacon_setup_node != "", 'EthereumServer::install: Ethereum Service has no beacon_setup_node.'

        bootnode_start_command = ""
        bc_start_command = LIGHTHOUSE_BN_CMD.format(eth_id=self.getId(),ip_address=addr, target_peers=self.__beacon_peer_counts)
        vc_start_command = ""
        wallet_create_command = ""
        validator_create_command = ""
        validator_deposit_sh = ""
        if self.__is_bootnode:
            bootnode_start_command = LIGHTHOUSE_BOOTNODE_CMD.format(ip_address=addr)
        if self.__is_beacon_validator_at_running:
            node.setFile('/tmp/seed.pass', 'seedseedseed')
            wallet_create_command = LIGHTHOUSE_WALLET_CREATE_CMD.format(eth_id=self.getId())
            validator_create_command = LIGHTHOUSE_VALIDATER_CREATE_CMD.format(eth_id=self.getId()) 
            node.setFile('/tmp/deposit.sh', VALIDATOR_DEPOSIT_SH.format(eth_id=self.getId()))
            node.appendStartCommand('chmod +x /tmp/deposit.sh')
            if not self.__is_manual_deposit_for_validator:
                validator_deposit_sh = "/tmp/deposit.sh"
        if self.__is_beacon_validator_at_genesis or self.__is_beacon_validator_at_running:
            vc_start_command = LIGHTHOUSE_VC_CMD.format(eth_id=self.getId(), ip_address=addr, acct_address=self.__accounts[0].getAddress())
            
        node.setFile('/tmp/beacon-setup-node', beacon_setup_node)
        node.setFile('/tmp/beacon-bootstrapper', EthServerFileTemplates['beacon_bootstrapper'].format( 
                                is_validator="true" if self.__is_beacon_validator_at_genesis else "false",
                                is_bootnode="true" if self.__is_bootnode else "false",
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
        """!
        @brief ETH server installation step.
        @param node node object
        @param eth reference to the eth service.
        @param allBootnode all-bootnode mode: all nodes are boot node.
        """

        if self.__enable_pos and self.__is_beacon_setup_node:
            beacon_setup_node = BeaconSetupServer(ttd=self.__terminal_total_difficulty)
            beacon_setup_node.install(node, eth)
            return 

        node.appendClassName('EthereumService')
        node.setLabel('node_id', self.getId())
        node.setLabel('consensus', self.__consensus_mechanism.value)

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumServer::install: node as{}/{} has no interfaces'.format(node.getAsn(), node.getName())
        addr = str(ifaces[0].getAddress())

        # update genesis.json
        if self.__consensus_mechanism == ConsensusMechanism.POA:
            self.__genesis.allocateBalance(eth.getAllAccounts())
            self.__genesis.setSigner(eth.getAllSignerAccounts())
    
        node.setFile('/tmp/eth-genesis.json', self.__genesis.getGenesis())
    
        # set account passwords to /tmp/eth-password
        account_passwords = []

        for account in self.__accounts:
            node.setFile("/tmp/keystore/"+account.getKeyStoreFileName(), account.getKeyStoreContent())
            account_passwords.append(account.getPassword())

        node.setFile('/tmp/eth-password', '\n'.join(account_passwords))

        # install required software
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
            node.appendStartCommand('python3 -m http.server {} -d /tmp'.format(self.__bootnode_http_port), True)

        # get other nodes IP for the bootstrapper.
        bootnodes = eth.getBootNodes(self.__consensus_mechanism)[:]
        if len(bootnodes) > 0 :
            node.setFile('/tmp/eth-nodes', '\n'.join(bootnodes))
            
            node.setFile('/tmp/eth-bootstrapper', EthServerFileTemplates['bootstrapper'])

            # load enode urls from other nodes
            node.appendStartCommand('chmod +x /tmp/eth-bootstrapper')
            node.appendStartCommand('/tmp/eth-bootstrapper')

        # launch Ethereum process.
        node.appendStartCommand(self.__generateGethStartCommand(), True) 
        
        if self.__enable_pos: 
            self.__install_beacon(node, eth)
                  
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
            self.__accounts_info[0] = (65 * pow(10, 18), "admin", None)
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

    def enablePoS(self, terminal_total_difficulty:int = 50) -> EthereumServer:
        """!
        @brief set configurations to enable PoS (Merge)

        @returns self, for chaining API calls
        """

        self.__enable_pos = True
        self.__terminal_total_difficulty = terminal_total_difficulty
        return self

    def isPoSEnabled(self) -> bool:
        """!
        @brief returns whether a node enabled PoS or not
        """
        return self.__enable_pos

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

    def setPreActivatedValidatorCount(self, count:int=10):
        self.__beacon_validator_count = count
        self.__accounts_info[0] = (32 * pow(10, 18)*(self.__beacon_validator_count+2), "admin", None)
        return self

    def enablePOSValidatorAtGenesis(self):
        self.__is_beacon_validator_at_genesis = True
        return self

    def isValidatorAtGenesis(self):
        return self.__is_beacon_validator_at_genesis

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

    def setBaseAccountBalance(self, balance:int):
        self.__accounts_info[0] = (balance, "admin", None)
        return self

    def setBeaconPeerCounts(self, peer_counts:int):
        self.__beacon_peer_counts = peer_counts
        return self
    
    def getBeaconSetupHttpPort(self) -> int:
        return self.__beacon_setup_http_port

    def setBeaconSetupHttpPort(self, port:int):
        self.__beacon_setup_http_port = port
        return self

    def setGasLimitPerBlock(self, gasLimit:int):
        """!
        @brief set GasLimit at Genesis 
        (the limit of gas cost per block)

        @param int
        
        @returns self, for chaining API calls
        """
        self.__genesis.setGasLimit(gasLimit)
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
DEPOSIT_CHAIN_ID: "10"
DEPOSIT_NETWORK_ID: "10"
MAX_COMMITTEES_PER_SLOT: "10"
INACTIVITY_PENALTY_QUOTIENT_BELLATRIX: "8"'''

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
while true; do {{
    lcli deploy-deposit-contract --eth1-http http://{geth_node_ip}:8545 --confirmations 1 --validator-count {validator_count} > contract_address.txt
    CONTRACT_ADDRESS=`head -1 contract_address.txt | cut -d '"' -f 2`
    if [[ $CONTRACT_ADDRESS = 0x* ]]; then
        break
    fi
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

    def install(self, node: Node, eth: EthereumService):
        """!
        @brief Install the service.
        """
        
        validator_ids = eth.getValidatorIds()
        validator_counts = len(validator_ids)

        bootnode_ip = eth.getBootNodes(self.__consensus_mechanism)[0].split(":")[0]
        
        node.addBuildCommand('apt-get update && apt-get install -y --no-install-recommends software-properties-common python3 python3-pip')
        node.addBuildCommand('pip install web3')
        node.appendStartCommand('lcli generate-bootnode-enr --ip {} --udp-port 30305 --tcp-port 30305 --genesis-fork-version 0x42424242 --output-dir /local-testnet/bootnode'.format(bootnode_ip))
        node.setFile("/tmp/config.yaml", self.BEACON_GENESIS.format(terminal_total_difficulty=self.__terminal_total_difficulty))
        node.setFile("/tmp/validator-ids", "\n".join(validator_ids))
        node.appendStartCommand('mkdir /local-testnet/testnet')
        node.appendStartCommand('bootnode_enr=`cat /local-testnet/bootnode/enr.dat`')
        node.appendStartCommand('echo "- $bootnode_enr" > /local-testnet/testnet/boot_enr.yaml')
        node.appendStartCommand('cp /tmp/config.yaml /local-testnet/testnet/config.yaml')
        node.appendStartCommand(self.DEPLOY_CONTRACT.format(geth_node_ip=bootnode_ip, validator_count = validator_counts))
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
