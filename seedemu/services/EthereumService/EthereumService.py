from __future__ import annotations

from .EthEnum import ConsensusMechanism, EthUnit
from .EthUtil import Genesis, EthAccount, AccountStructure
from .EthereumServer import EthereumServer, PoAServer, PoWServer, PoSServer
from os import mkdir, path, makedirs, rename
from seedemu.core import Node, Service, Server, Emulator
from seedemu.core.enums import NetworkType
from .FaucetServer import FaucetServer
from .EthUtilityServer import EthUtilityServer
from typing import Dict, List
from sys import stderr

class Blockchain:
    """!
    @brief The individual blockchain in EthereumService.
    This Blockchain class allows to maintain multiple blockchains inside EthereumService.
    """
    _consensus: ConsensusMechanism
    _genesis: Genesis
    _eth_service: EthereumService
    _boot_node_addresses: Dict[ConsensusMechanism, List[str]]
    _joined_accounts: List[AccountStructure]
    _joined_signer_accounts: List[AccountStructure]
    _validator_ids: List[str]
    _beacon_setup_node_address: str
    _chain_id:int
    _pending_targets:list
    _chain_name:str
    _emu_mnemonic:str
    _total_accounts_per_node: int
    _emu_account_balance: int
    _local_mnemonic:str
    _local_accounts_total:int
    _local_account_balance:int
    _terminal_total_difficulty:int
    _target_aggregater_per_committee:int
    _target_committee_size:int

    def __init__(self, service:EthereumService, chainName: str, chainId: int, consensus:ConsensusMechanism):
        """!
        @brief The Blockchain class initializer.

        @param service The EthereumService that creates the Blockchain class instance.
        @param chainName The name of the Blockchain to create.
        @param chainid The chain id of the Blockchain to create.
        @param consensus The consensus of the Blockchain to create (supports POA, POS, POW).

        @returns An instance of The Blockchain class.
        """
        self._eth_service = service
        self._consensus = consensus
        self._chain_name = chainName
        self._genesis = Genesis(ConsensusMechanism.POA) if self._consensus == ConsensusMechanism.POS else Genesis(self._consensus)
        self._boot_node_addresses = []
        self._miner_node_address = []
        self._joined_accounts = []
        self._joined_signer_accounts = []
        self._validator_ids = []
        self._beacon_setup_node_address = ''
        self._pending_targets = []
        self._emu_mnemonic = "great awesome fun seed security lab protect system network prevent attack future"
        self._total_accounts_per_node = 1
        self._emu_account_balance = 32 * EthUnit.ETHER.value
        self._local_mnemonic = "great amazing fun seed lab protect network system security prevent attack future"
        self._local_accounts_total = 5
        self._local_account_balance = 10 * EthUnit.ETHER.value
        self._chain_id = chainId
        self._terminal_total_difficulty = 20
        self._target_aggregater_per_committee = 2
        self._target_committee_size = 3
        

    def _doConfigure(self, node:Node, server:Server):
        if isinstance(server, FaucetServer):
            self._log('configuring as{}/{} as an faucet node...'.format(node.getAsn(), node.getName()))
            self.addLocalAccount(server.getFaucetAddress(), balance=server.getFaucetBalance())
            return   

        if isinstance(server, EthUtilityServer):
            self._log('configuring as{}/{} as an eth init and info node...'.format(node.getAsn(), node.getName()))
            return
        
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())
        
        if server.isBootNode():
            self._log('adding as{}/{} as consensus-{} bootnode...'.format(node.getAsn(), node.getName(), self._consensus.value))
            self._boot_node_addresses.append(addr)
        
        if self._consensus == ConsensusMechanism.POS:
            if server.isStartMiner():
                self._log('adding as{}/{} as consensus-{} miner...'.format(node.getAsn(), node.getName(), self._consensus.value))
                self._miner_node_address.append(str(ifaces[0].getAddress())) 
            if server.isBeaconSetupNode():
                self._beacon_setup_node_address = '{}:{}'.format(ifaces[0].getAddress(), server.getBeaconSetupHttpPort())

        server._createAccounts(self)
        
        accounts = server._getAccounts()
        if len(accounts) > 0:
            if self._consensus == ConsensusMechanism.POS and server.isValidatorAtRunning():
                accounts[0].balance = 33 * EthUnit.ETHER.value
            self._joined_accounts.extend(accounts)
            if self._consensus in [ConsensusMechanism.POA, ConsensusMechanism.POS] and server.isStartMiner():
                self._joined_signer_accounts.append(accounts[0])

        if self._consensus == ConsensusMechanism.POS and server.isValidatorAtGenesis():
            self._validator_ids.append(str(server.getId()))
        
        server._generateGethStartCommand()

        if self._eth_service.isSave():
            save_path = self._eth_service.getSavePath()
            node.addSharedFolder('/root/.ethereum', '../{}/{}/{}/ethereum'.format(save_path, self._chain_name, server.getId()))
            node.addSharedFolder('/root/.ethash', '../{}/{}/{}/ethash'.format(save_path, self._chain_name, server.getId()))
            makedirs('{}/{}/{}/ethereum'.format(save_path, self._chain_name, server.getId()))
            makedirs('{}/{}/{}/ethash'.format(save_path, self._chain_name, server.getId()))

    def configure(self, emulator:Emulator):
        pending_targets = self._eth_service.getPendingTargets()
        localAccounts = EthAccount.createLocalAccountsFromMnemonic(mnemonic=self._local_mnemonic, balance=self._local_account_balance, total=self._local_accounts_total)
        self._genesis.addAccounts(localAccounts)
        self._genesis.setChainId(self._chain_id)
        for vnode in self._pending_targets:
            node = emulator.getBindingFor(vnode)
            server = pending_targets[vnode]
            if isinstance(server, FaucetServer):
                server.__class__ = FaucetServer
                linked_eth_node_name = server.getLinkedEthNodeName()
                assert linked_eth_node_name != ''  or server.getEthServerUrl() !='' , 'both rpc url and eth node are not set'
                server.setEthServerUrl(self.__getIpByVnodeName(emulator, linked_eth_node_name))
                eth_server: EthereumServer = emulator.getServerByVirtualNodeName(linked_eth_node_name)
                server.setEthServerPort(eth_server.getGethHttpPort())

            elif isinstance(server, EthUtilityServer):
                server.__class__ = EthUtilityServer
                linked_eth_node_name = server.getLinkedEthNodeName()
                assert linked_eth_node_name != '' , 'linked eth node is not set'
                server.setEthServerUrl(self.__getIpByVnodeName(emulator, linked_eth_node_name))
                eth_server: EthereumServer = emulator.getServerByVirtualNodeName(linked_eth_node_name)
                server.setEthServerPort(eth_server.getGethHttpPort())

                linked_faucet_node_name = server.getLinkedFaucetNodeName()
                assert linked_faucet_node_name != '' , 'linked faucet node is not set'
                server.setFaucetUrl(self.__getIpByVnodeName(emulator, linked_faucet_node_name))
                faucet_server:FaucetServer = emulator.getServerByVirtualNodeName(linked_faucet_node_name)
                server.setFaucetPort(faucet_server.getPort())

            elif self._consensus == ConsensusMechanism.POS and server.isStartMiner():

                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
                addr = str(ifaces[0].getAddress())
                miner_ip = self._miner_node_address[0]
                if addr == miner_ip:
                    validator_count = len(self.getValidatorIds())
                    index = self._joined_accounts.index(server._getAccounts()[0])
                    self._joined_accounts[index].balance = 32*pow(10,18)*(validator_count+2)
        
        self._genesis.addAccounts(self.getAllAccounts())
        
        if self._consensus in [ConsensusMechanism.POA, ConsensusMechanism.POS] :
            self._genesis.setSigner(self.getAllSignerAccounts())
    
    def __getIpByVnodeName(self, emulator, nodename:str) -> str:
        node = emulator.getBindingFor(nodename)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                return address
    
    def getAllServerNames(self):
        server_names = {}
        pending_targets = self._eth_service.getPendingTargets()
        for key, value in pending_targets.items():
            if key in self._pending_targets:
                server_type = value.__class__.__name__
                if value.__class__.__name__ not in server_names.keys():
                    server_names[server_type] = []
                server_names[server_type].append(key)
        return server_names

    def getBootNodes(self) -> List[str]:
        """!
        @brief Get bootnode IPs.

        @returns List of bootnodes IP addresses.
        """
        return self._boot_node_addresses

    def getMinerNodes(self) -> List[str]:
        """!
        @brief Get miner node IPs.

        @returns List of miner nodes IP addresses.
        """
        return self._miner_node_address

    def getAllAccounts(self) -> List[AccountStructure]:
        """!
        @brief Get a joined list of all the created accounts on all nodes in the blockchain.
        
        @returns List of accounts.
        """
        return self._joined_accounts

    def getAllSignerAccounts(self) -> List[AccountStructure]:
        """!
        @brief Get a list of all signer accounts on all nodes in the blockchain.
        
        returns List of signer accounts.
        """
        return self._joined_signer_accounts

    def getValidatorIds(self) -> List[str]:
        """!
        @brief Get a list of all validators ids on all nodes in the blockchain.
        
        @returns List of all validators ids.
        """
        return self._validator_ids

    def getBeaconSetupNodeIp(self) -> str:
        """!
        @brief Get the IP of a beacon setup node.

        @returns The IP address.
        """
        return self._beacon_setup_node_address

    def setGenesis(self, genesis:str) -> EthereumServer:
        """!
        @brief Set the custom genesis.
        
        @param genesis The genesis file contents to set. 

        @returns Self, for chaining API calls.
        """
        self._genesis.setGenesis(genesis)

        return self

    def getGenesis(self) -> Genesis:
        """!
        @brief Get the genesis file content.

        @returns Genesis. 
        """
        return self._genesis

    def setConsensusMechanism(self, consensus:ConsensusMechanism) -> EthereumServer:
        """!
        @brief Set consensus mechanism of this blockchain.

        @param consensusMechanism Consensus mechanism to set (supports POW, POA and POS).

        @returns Self, for chaining API calls. 
        """
        self._consensus = consensus
        self._genesis = Genesis(self._consensus)
        
        return self

    def getConsensusMechanism(self) -> ConsensusMechanism:
        """!
        @brief Get the consensus mechanism of this blockchain.

        @returns ConsensusMechanism
        """
        return self._consensus
    
    def setTerminalTotalDifficulty(self, ttd:int):
        """!
        @brief Set the terminal total difficulty, which is the value to designate
                when the Merge is happen. In POA, difficulty is tend to increase by 2
                for every one block. For example, if the terminal_total_difficulty is 
                set to 20, the Ethereum blockchain will keep POA consensus for approximately
                150 sec (20/2*15) and then stop signing the block until the Merge happens.
                Default to 20. 

        @param ttd The terminal total difficulty to set.
        
        @returns Self, for chaining API calls.
        """
        self._terminal_total_difficulty = ttd

        return self

    def getTerminalTotalDifficulty(self) -> int:
        """!
        @brief Get the value of the terminal total difficulty.
        
        @returns terminal_total_difficulty.
        """

        return self._terminal_total_difficulty

    def setGasLimitPerBlock(self, gasLimit:int):
        """!
        @brief Set GasLimit at Genesis (the limit of gas cost per block).

        @param gasLimit The gas limit per block.
        
        @returns Self, for chaining API calls.
        """
        self._genesis.setGasLimit(gasLimit)
        return self

    def setChainId(self, chainId:int):
        """!
        @brief Set chain Id at Genesis.

        @param chainId The chain Id to set.

        @returns Self, for chaining API calls
        """

        self._chain_id = chainId
        return self

    def createNode(self, vnode: str) -> EthereumServer:
        """!
        @brief Create a node belongs to this blockchain.

        @param vnode The name of vnode.

        @returns EthereumServer
        """
        eth = self._eth_service
        self._pending_targets.append(vnode)
        return eth.installByBlockchain(vnode, self)
    
    def addCode(self, address: str, code: str) -> Blockchain:
        """!
        @brief Add code to an account by setting code field of genesis file.

        @param address The account's address.
        @param code The code to set.

        @returns Self, for chaining calls.
        """
        self._genesis.addCode(address, code)
        return self
    
    def addLocalAccount(self, address: str, balance: int, unit:EthUnit=EthUnit.ETHER) -> Blockchain:
        """!
        @brief Allocate balance to an external account by setting alloc field of genesis file.

        @param address The External account's address.
        @param balance The balance to allocate.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        balance = balance * unit.value
        self._genesis.addLocalAccount(address, balance)
        
        return self

    def addLocalAccountsFromMnemonic(self, mnemonic:str, total:int, balance:int, unit:EthUnit=EthUnit.ETHER) -> Blockchain:
        """!
        @brief Add local account from the given Mnemonic in addition to default local accounts.

        @param mnemonic The mnemonic phrase to generate accounts from.
        @param total The total number of accounts to generate.
        @param balance The balance to allocate to the generated accounts.

        @returns Self, for chaining calls.
        """
        balance = balance * unit.value
        mnemonic_account = EthAccount.createLocalAccountsFromMnemonic(mnemonic = mnemonic, balance=balance, total=total)
        self._genesis.addAccounts(mnemonic_account)

    def getChainName(self) -> str:
        """!
        @brief Get the name of the blockchain.

        @returns The name of this blockchain.
        """
        return self._chain_name

    def getChainId(self) -> int:
        """!
        @brief Get the chain Id of the blockchain.
        
        @returns The chain Id of this blockchain.
        """
        return self._chain_id

    def setEmuAccountParameters(self, mnemonic:str, balance:int, total_per_node:int, unit:EthUnit=EthUnit.ETHER):
        """!
        @brief Set mnemonic, balance, and total_per_node value to customize the account generation in this blockchain.

        @param mnemonic The mnemonic phrase to generate the accounts per a node in this blockchain.
        @param balance The balance to allocate to the generated accounts.
        @param total_per_node The total number of the accounts to generate per a node in this blockchain.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        self._emu_mnemonic = mnemonic
        self._emu_account_balance = balance * unit.value
        self._total_accounts_per_node = total_per_node
        return self

    def getEmuAccountParameters(self):
        """!
        @brief Get values of mnemonic, balance, and total_per_node value used for the account generation.
        
        returns The value of mnemonic, balance, and total_per_node.
        """
        return self._emu_mnemonic, self._emu_account_balance, self._total_accounts_per_node

    def setLocalAccountParameters(self, mnemonic:str, balance:int, total:int, unit:EthUnit=EthUnit.ETHER):
        """!
        @brief Set mnemonic, balance, and total_per_node value to customize the local account generation.

        @param mnemonic The mnemonic phrase to generate the local accounts.
        @param balance The balance to allocate to the generated accounts.
        @param total The total number of the local accounts.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        self._local_mnemonic = mnemonic
        self._local_account_balance = balance * unit.value
        self._local_accounts_total = total
        return self

    def setTargetAggregatorPerCommittee(self, target_aggregator_per_committee:int):
        """!
        @brief Set target aggregator per committee for Beacon chain.
        
        @param target_aggregator_per_committee The target value of the number of aggregator per committee to set.
        
        @returns Self, for chaining calls.
        """
        self._target_aggregater_per_committee = target_aggregator_per_committee
        return self

    def getTargetAggregatorPerCommittee(self):
        """!
        @brief Get the value of target aggregator per committee for Beacon chain.
        
        @returns The value of target_aggregator_per_committee.
        """
        return self._target_aggregater_per_committee

    def setTargetCommitteeSize(self, target_committee_size:int):
        """!
        @brief Set target committee size for Beacon chain.

        @param target_committee_size The target value of committee size to set.

        @returns Self, for chaining calls.
        """
        self._target_committee_size = target_committee_size
        return self

    def getTargetCommitteeSize(self):
        """!
        @brief Get the value of target committee size for Beacon Chain.

        @returns The value of target_committee_size.
        """
        return self._target_committee_size
    
    def createEthUtilityServer(self, vnode:str, port:int, linked_eth_node:str, linked_faucet_node:str):
        """!
        @brief Create an EthUtilityServer Server that can deploy contract and runs webserver to provide contract address info.

        @returns self, for chaining calls
        """
        eth = self._eth_service
        self._pending_targets.append(vnode)
        return eth.installEthUtilityServer(vnode, self, port, linked_eth_node, linked_faucet_node)
    
    def createFaucetServer(self, vnode:str, port:int, linked_eth_node:str, balance=1000, max_fund_amount=10):
        """!
        @brief Create a Faucet Server that can fund ethereum accounts using http api.
        
        @param vnode: name of faucet server vnode.
        @param port: port number of Faucet http server.
        @param linked_eth_node: vnode name of eth node to link.
        @param balance: balance of the faucet account. (unit: ETH)

        @returns self, for chaining calls.
        """
        eth = self._eth_service
        self._pending_targets.append(vnode)
        return eth.installFaucet(vnode, self, linked_eth_node, port, balance, max_fund_amount)


    def getFaucetServerByName(self, vnode: str) -> FaucetServer:
        """!
        @brief Return an instance of the faucet server based on the provided name.

        @param vnode: name of the faucet server

        @returns an instance of FaucetServer
        """

        pending_targets = self._eth_service.getPendingTargets()
        if vnode in self._pending_targets: 
            if isinstance(pending_targets[vnode], FaucetServer):
               return pending_targets[vnode]
        return None

    
    def getFaucetServerInfo(self) -> List[Dict]:
        faucetInfo = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, FaucetServer):
                info = {}
                info['name'] = key
                info['port'] = value.getPort()
                faucetInfo.append(info)
        return faucetInfo

    def getFaucetServerNames(self) -> List[str]:
        faucetServerNames = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, FaucetServer):
                faucetServerNames.append(key)
        return faucetServerNames
    
    def getEthServerNames(self) -> List[str]:
        ethServerNames = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, EthereumServer):
                ethServerNames.append(key)
        return ethServerNames

    def getEthServerInfo(self) -> List[Dict]:
        ethInfo = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, EthereumServer):
                info = {}
                info['name'] = key
                info['geth_http_port'] = value.getGethHttpPort()
                info['geth_ws_port'] = value.getGethWsPort()
                ethInfo.append(info)
        return ethInfo

    def getUtilityServerByName(self, vnode: str) -> EthUtilityServer:
        """!
        @brief Return an instance of the utility server based on the provided name.

        @param vnode: name of the server
 
        @returns an instance of EthUtilityServer
        """

        pending_targets = self._eth_service.getPendingTargets()
        if vnode in self._pending_targets: 
            if isinstance(pending_targets[vnode], EthUtilityServer):
               return pending_targets[vnode]
        return None

    def getUtilityServerNames(self) -> List[str]:
        ethUtilityServerNames = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, EthUtilityServer):
                ethUtilityServerNames.append(key)
        return ethUtilityServerNames
    
    def getUtilityServerInfo(self) -> List[Dict]:
        ethUtilityServerInfo = []
        for key, value in self._eth_service.getPendingTargets().items():
            if key in self._pending_targets and isinstance(value, EthUtilityServer):
                info = {}
                info['name'] = key
                info['port'] = value.getPort()
                ethUtilityServerInfo.append(info)
        return ethUtilityServerInfo


    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.

        @returns None.
        """
        print("==== Blockchain Sub Layer: {}".format(message), file=stderr)


class EthereumService(Service):
    """!
    @brief The Ethereum network service.
    This service allows one to run a private Ethereum network in the emulator.
    """

    __blockchains: Dict[str, Blockchain]

    __save_state: bool
    __save_path: str
    __override: bool
    __blockchain_id: int
    __serial: int

    def __init__(self, saveState: bool = False, savePath: str = './eth-states', override:bool=False):
        """!
        @brief The EthereumService class initializer.

        @param saveState (optional) If true, the service will try to save state
        of the block chain by saving the datadir of every node. Default to
        false.
        @param savePath (optional) The path to save containers' datadirs on the
        host. Default to "./eth-states". 
        @param override (optional) If true, override the output folder if it already
        exist. False by default.

        @returns An instance of the EthereumService class.
        """
        super().__init__()

        self.__serial = 0
        self.__save_state = saveState
        self.__save_path = savePath
        self.__override = override
        self.__blockchains = {}
        self.__blockchain_id = 1337

    def getName(self):
        return 'EthereumService'
    
    def getAllServerNames(self):
        server_names = {}
        for chain_name, blockchain_obj in self.__blockchains.items():
            server_names[chain_name] = blockchain_obj.getAllServerNames()

        return server_names

    def isSave(self):
        return self.__save_state

    def getSavePath(self):
        return self.__save_path

    def _doConfigure(self, node: Node, server: EthereumServer):
        blockchain = server.getBlockchain()
        blockchain._doConfigure(node, server)
    
    def configure(self, emulator: Emulator):
        if self.__save_state:
            self._createSharedFolder()
        super().configure(emulator)
        for blockchain in self.__blockchains.values():
            blockchain.configure(emulator)
        
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
        
    def _doInstall(self, node: Node, server: Server):
        self._log('installing eth on as{}/{}...'.format(node.getAsn(), node.getName()))
        if isinstance(server, EthereumServer):
            server.install(node, self)
        elif isinstance(server, FaucetServer):
            server.install(node)
        elif isinstance(server, EthUtilityServer):
            server.install(node)

    def _createServer(self, blockchain: Blockchain = None) -> Server:
        self.__serial += 1
        assert blockchain != None, 'EthereumService::_createServer(): create server using Blockchain::createNode() not EthereumService::install()'.format()
        consensus = blockchain.getConsensusMechanism()
        if consensus == ConsensusMechanism.POA:
            return PoAServer(self.__serial, blockchain)
        if consensus == ConsensusMechanism.POW:
            return PoWServer(self.__serial, blockchain)
        if consensus == ConsensusMechanism.POS:
            return PoSServer(self.__serial, blockchain)
        
    def _createFaucetServer(self, blockchain:Blockchain, linked_eth_node:str, port:int, balance:int, max_fund_amount:int) -> FaucetServer:
        return FaucetServer(blockchain, linked_eth_node, port, balance, max_fund_amount)

    def _createEthUtilityServer(self, blockchain:Blockchain, port:int, linked_eth_node:str, linked_faucet_node:str) -> EthUtilityServer:
        return EthUtilityServer(blockchain, port, linked_eth_node, linked_faucet_node)

    def installByBlockchain(self, vnode: str, blockchain: Blockchain) -> EthereumServer:
        """!
        @brief Install the service on a node identified by given name. 
                This API is called by Blockchain Class. 

        @param vnode The name of the virtual node. 
        @param blockchain The blockchain that the created node is belongs to.
        
        @returns EthereumServer.
        """
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createServer(blockchain)
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]

    def installFaucet(self, vnode:str, blockchain:Blockchain, linked_eth_node:str, port:int=80, balance:int=1000, max_fund_amount:int=10) -> FaucetServer:
        """!
        @brief Install the server on a node identified by given name.
        """
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createFaucetServer(blockchain, linked_eth_node, port, balance, max_fund_amount)
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]
    
    def installEthUtilityServer(self, vnode:str, blockchain:Blockchain, port:int, linked_eth_node:str, linked_faucet_node:str):
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createEthUtilityServer(blockchain, port, linked_eth_node, linked_faucet_node)
        self._pending_targets[vnode] = s
        
        return self._pending_targets[vnode]

    def getBlockchainNames(self) -> List[str]:
        """!
        @brief Get installed blockchain names.

        @returns a list of blockchain name
        """
        blockchainNames = [chainName for chainName in self.__blockchains.keys()]
        return blockchainNames
    
    def getBlockchainByName(self, blockchainName) -> Blockchain:
        """!
        @brief get Blockchain object by its name

        @returns a blockchain object
        """
        return self.__blockchains[blockchainName]
    
    
        

    
    def createBlockchain(self, chainName:str, consensus: ConsensusMechanism, chainId: int = -1):
        """!
        @brief Create an instance of Blockchain class which is a sub-layer of the EthereumService.

        @param chainName The name of the Blockchain.
        @param consensus The consensus mechanism of the blockchain.
        @param chainId The chain id of the Blockchain.

        @returns an instance of Blockchain class.
        """
        
        if chainId < 0 : 
            chainId = self.__blockchain_id
            self.__blockchain_id += 1
        blockchain = Blockchain(self, chainName, chainId, consensus)
        self.__blockchains[chainName] = blockchain
        return blockchain

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
