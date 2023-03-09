from __future__ import annotations

from .EthEnum import ConsensusMechanism, EthUnit
from .EthUtil import Genesis, EthAccount, AccountStructure
from .EthereumServer import EthereumServer, PoAServer, PoWServer, PoSServer
from os import mkdir, path, makedirs, rename
from seedemu.core import Node, Service, Server, Emulator
from typing import Dict, List
from sys import stderr

class Blockchain:
    """!
    @brief The individual blockchain in EthereumService.
    This Blockchain class allows to maintain multiple blockchains inside EthereumService.
    """
    __consensus: ConsensusMechanism
    __genesis: Genesis
    __eth_service: EthereumService
    __boot_node_addresses: Dict[ConsensusMechanism, List[str]]
    __joined_accounts: List[AccountStructure]
    __joined_signer_accounts: List[AccountStructure]
    __validator_ids: List[str]
    __beacon_setup_node_address: str
    __chain_id:int
    __pending_targets:list
    __chain_name:str
    __emu_mnemonic:str
    __total_accounts_per_node: int
    __emu_account_balance: int
    __local_mnemonic:str
    __local_accounts_total:int
    __local_account_balance:int
    __terminal_total_difficulty:int
    __target_aggregater_per_committee:int
    __target_committee_size:int

    def __init__(self, service:EthereumService, chainName: str, chainId: int, consensus:ConsensusMechanism):
        """!
        @brief The Blockchain class initializer.

        @param service The EthereumService that creates the Blockchain class instance.
        @param chainName The name of the Blockchain to create.
        @param chainid The chain id of the Blockchain to create.
        @param consensus The consensus of the Blockchain to create (supports POA, POS, POW).

        @returns An instance of The Blockchain class.
        """
        self.__eth_service = service
        self.__consensus = consensus
        self.__chain_name = chainName
        self.__genesis = Genesis(ConsensusMechanism.POA) if self.__consensus == ConsensusMechanism.POS else Genesis(self.__consensus)
        self.__boot_node_addresses = []
        self.__miner_node_address = []
        self.__joined_accounts = []
        self.__joined_signer_accounts = []
        self.__validator_ids = []
        self.__beacon_setup_node_address = ''
        self.__pending_targets = []
        self.__emu_mnemonic = "great awesome fun seed security lab protect system network prevent attack future"
        self.__total_accounts_per_node = 1
        self.__emu_account_balance = 32 * EthUnit.ETHER.value
        self.__local_mnemonic = "great amazing fun seed lab protect network system security prevent attack future"
        self.__local_accounts_total = 5
        self.__local_account_balance = 10 * EthUnit.ETHER.value
        self.__chain_id = chainId
        self.__terminal_total_difficulty = 20
        self.__target_aggregater_per_committee = 2
        self.__target_committee_size = 3

    def _doConfigure(self, node:Node, server:EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())
        
        if server.isBootNode():
            self._log('adding as{}/{} as consensus-{} bootnode...'.format(node.getAsn(), node.getName(), self.__consensus.value))
            self.__boot_node_addresses.append(addr)
        
        if self.__consensus == ConsensusMechanism.POS:
            if server.isStartMiner():
                self._log('adding as{}/{} as consensus-{} miner...'.format(node.getAsn(), node.getName(), self.__consensus.value))
                self.__miner_node_address.append(str(ifaces[0].getAddress())) 
            if server.isBeaconSetupNode():
                self.__beacon_setup_node_address = '{}:{}'.format(ifaces[0].getAddress(), server.getBeaconSetupHttpPort())

        server._createAccounts(self)
        
        accounts = server._getAccounts()
        if len(accounts) > 0:
            if self.__consensus == ConsensusMechanism.POS and server.isValidatorAtRunning():
                accounts[0].balance = 33 * EthUnit.ETHER.value
            self.__joined_accounts.extend(accounts)
            if self.__consensus in [ConsensusMechanism.POA, ConsensusMechanism.POS] and server.isStartMiner():
                self.__joined_signer_accounts.append(accounts[0])

        if self.__consensus == ConsensusMechanism.POS and server.isValidatorAtGenesis():
            self.__validator_ids.append(str(server.getId()))
        
        server._generateGethStartCommand()

        if self.__eth_service.isSave():
            save_path = self.__eth_service.getSavePath()
            node.addSharedFolder('/root/.ethereum', '../{}/{}/{}/ethereum'.format(save_path, self.__chain_name, server.getId()))
            node.addSharedFolder('/root/.ethash', '../{}/{}/{}/ethash'.format(save_path, self.__chain_name, server.getId()))
            makedirs('{}/{}/{}/ethereum'.format(save_path, self.__chain_name, server.getId()))
            makedirs('{}/{}/{}/ethash'.format(save_path, self.__chain_name, server.getId()))

    def configure(self, emulator:Emulator):
        pending_targets = self.__eth_service.getPendingTargets()
        localAccounts = EthAccount.createLocalAccountsFromMnemonic(mnemonic=self.__local_mnemonic, balance=self.__local_account_balance, total=self.__local_accounts_total)
        self.__genesis.addAccounts(localAccounts)
        self.__genesis.setChainId(self.__chain_id)
        for vnode in self.__pending_targets:
            node = emulator.getBindingFor(vnode)
            server = pending_targets[vnode]
            if self.__consensus == ConsensusMechanism.POS and server.isStartMiner():
                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
                addr = str(ifaces[0].getAddress())
                miner_ip = self.__miner_node_address[0]
                if addr == miner_ip:
                    validator_count = len(self.getValidatorIds())
                    index = self.__joined_accounts.index(server._getAccounts()[0])
                    self.__joined_accounts[index].balance = 32*pow(10,18)*(validator_count+2)
        
        self.__genesis.addAccounts(self.getAllAccounts())
        
        if self.__consensus in [ConsensusMechanism.POA, ConsensusMechanism.POS] :
            self.__genesis.setSigner(self.getAllSignerAccounts())
    
    def getBootNodes(self) -> List[str]:
        """!
        @brief Get bootnode IPs.

        @returns List of bootnodes IP addresses.
        """
        return self.__boot_node_addresses

    def getMinerNodes(self) -> List[str]:
        """!
        @brief Get miner node IPs.

        @returns List of miner nodes IP addresses.
        """
        return self.__miner_node_address

    def getAllAccounts(self) -> List[AccountStructure]:
        """!
        @brief Get a joined list of all the created accounts on all nodes in the blockchain.
        
        @returns List of accounts.
        """
        return self.__joined_accounts

    def getAllSignerAccounts(self) -> List[AccountStructure]:
        """!
        @brief Get a list of all signer accounts on all nodes in the blockchain.
        
        returns List of signer accounts.
        """
        return self.__joined_signer_accounts

    def getValidatorIds(self) -> List[str]:
        """!
        @brief Get a list of all validators ids on all nodes in the blockchain.
        
        @returns List of all validators ids.
        """
        return self.__validator_ids

    def getBeaconSetupNodeIp(self) -> str:
        """!
        @brief Get the IP of a beacon setup node.

        @returns The IP address.
        """
        return self.__beacon_setup_node_address

    def setGenesis(self, genesis:str) -> EthereumServer:
        """!
        @brief Set the custom genesis.
        
        @param genesis The genesis file contents to set. 

        @returns Self, for chaining API calls.
        """
        self.__genesis.setGenesis(genesis)

        return self

    def getGenesis(self) -> Genesis:
        """!
        @brief Get the genesis file content.

        @returns Genesis. 
        """
        return self.__genesis

    def setConsensusMechanism(self, consensus:ConsensusMechanism) -> EthereumServer:
        """!
        @brief Set consensus mechanism of this blockchain.

        @param consensusMechanism Consensus mechanism to set (supports POW, POA and POS).

        @returns Self, for chaining API calls. 
        """
        self.__consensus = consensus
        self.__genesis = Genesis(self.__consensus)
        
        return self

    def getConsensusMechanism(self) -> ConsensusMechanism:
        """!
        @brief Get the consensus mechanism of this blockchain.

        @returns ConsensusMechanism
        """
        return self.__consensus
    
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
        self.__terminal_total_difficulty = ttd

        return self

    def getTerminalTotalDifficulty(self) -> int:
        """!
        @brief Get the value of the terminal total difficulty.
        
        @returns terminal_total_difficulty.
        """

        return self.__terminal_total_difficulty

    def setGasLimitPerBlock(self, gasLimit:int):
        """!
        @brief Set GasLimit at Genesis (the limit of gas cost per block).

        @param gasLimit The gas limit per block.
        
        @returns Self, for chaining API calls.
        """
        self.__genesis.setGasLimit(gasLimit)
        return self

    def setChainId(self, chainId:int):
        """!
        @brief Set chain Id at Genesis.

        @param chainId The chain Id to set.

        @returns Self, for chaining API calls
        """

        self.__chain_id = chainId
        return self

    def createNode(self, vnode: str) -> EthereumServer:
        """!
        @brief Create a node belongs to this blockchain.

        @param vnode The name of vnode.

        @returns EthereumServer
        """
        eth = self.__eth_service
        self.__pending_targets.append(vnode)
        return eth.installByBlockchain(vnode, self)
    
    def addLocalAccount(self, address: str, balance: int, unit:EthUnit=EthUnit.ETHER) -> Blockchain:
        """!
        @brief Allocate balance to an external account by setting alloc field of genesis file.

        @param address The External account's address.
        @param balance The balance to allocate.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        balance = balance * unit.value
        self.__genesis.addLocalAccount(address, balance)
        
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
        self.__genesis.addAccounts(mnemonic_account)

    def getChainName(self) -> str:
        """!
        @brief Get the name of the blockchain.

        @returns The name of this blockchain.
        """
        return self.__chain_name

    def getChainId(self) -> int:
        """!
        @brief Get the chain Id of the blockchain.
        
        @returns The chain Id of this blockchain.
        """
        return self.__chain_id

    def setEmuAccountParameters(self, mnemonic:str, balance:int, total_per_node:int, unit:EthUnit=EthUnit.ETHER):
        """!
        @brief Set mnemonic, balance, and total_per_node value to customize the account generation in this blockchain.

        @param mnemonic The mnemonic phrase to generate the accounts per a node in this blockchain.
        @param balance The balance to allocate to the generated accounts.
        @param total_per_node The total number of the accounts to generate per a node in this blockchain.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        self.__emu_mnemonic = mnemonic
        self.__emu_account_balance = balance * unit.value
        self.__total_accounts_per_node = total_per_node
        return self

    def getEmuAccountParameters(self):
        """!
        @brief Get values of mnemonic, balance, and total_per_node value used for the account generation.
        
        returns The value of mnemonic, balance, and total_per_node.
        """
        return self.__emu_mnemonic, self.__emu_account_balance, self.__total_accounts_per_node

    def setLocalAccountParameters(self, mnemonic:str, balance:int, total:int, unit:EthUnit=EthUnit.ETHER):
        """!
        @brief Set mnemonic, balance, and total_per_node value to customize the local account generation.

        @param mnemonic The mnemonic phrase to generate the local accounts.
        @param balance The balance to allocate to the generated accounts.
        @param total The total number of the local accounts.
        @param unit The unit of Ethereum.

        @returns Self, for chaining calls.
        """
        self.__local_mnemonic = mnemonic
        self.__local_account_balance = balance * unit.value
        self.__local_accounts_total = total
        return self

    def setTargetAggregatorPerCommittee(self, target_aggregator_per_committee:int):
        """!
        @brief Set target aggregator per committee for Beacon chain.
        
        @param target_aggregator_per_committee The target value of the number of aggregator per committee to set.
        
        @returns Self, for chaining calls.
        """
        self.__target_aggregater_per_committee = target_aggregator_per_committee
        return self

    def getTargetAggregatorPerCommittee(self):
        """!
        @brief Get the value of target aggregator per committee for Beacon chain.
        
        @returns The value of target_aggregator_per_committee.
        """
        return self.__target_aggregater_per_committee

    def setTargetCommitteeSize(self, target_committee_size:int):
        """!
        @brief Set target committee size for Beacon chain.

        @param target_committee_size The target value of committee size to set.

        @returns Self, for chaining calls.
        """
        self.__target_committee_size = target_committee_size
        return self

    def getTargetCommitteeSize(self):
        """!
        @brief Get the value of target committee size for Beacon Chain.

        @returns The value of target_committee_size.
        """
        return self.__target_committee_size

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
        
    def _doInstall(self, node: Node, server: EthereumServer):
        self._log('installing eth on as{}/{}...'.format(node.getAsn(), node.getName()))

        server.install(node, self)

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
