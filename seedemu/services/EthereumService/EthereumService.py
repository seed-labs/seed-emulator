from __future__ import annotations

from .EthEnum import ConsensusMechanism
from .EthUtil import Genesis, EthAccount
from .EthereumServer import *

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
    __joined_accounts: List[EthAccount]
    __joined_signer_accounts: List[EthAccount]
    __validator_ids: List[str]
    __beacon_setup_node_address: str
    __chain_id:int
    __pending_targets:list
    __chain_name:str

    def __init__(self, service:EthereumService, chainName: str, consensus:ConsensusMechanism):
        self.__eth_service = service
        self.__consensus = consensus
        self.__chain_name = chainName
        self.__genesis = Genesis(self.__consensus)
        self.__boot_node_addresses = []
        self.__joined_accounts = []
        self.__joined_signer_accounts = []
        self.__validator_ids = []
        self.__beacon_setup_node_address = ''
        self.__pending_targets = []

    def _doConfigure(self, node:Node, server:EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())
        
        if server.isBootNode():
            self._log('adding as{}/{} as consensus-{} bootnode...'.format(node.getAsn(), node.getName(), self.__consensus.value))
            self.__boot_node_addresses.append(addr)

        if self.__consensus == ConsensusMechanism.POS and server.isBeaconSetupNode():
            self.__beacon_setup_node_address = '{}:{}'.format(ifaces[0].getAddress(), server.getBeaconSetupHttpPort())

        server._createAccounts(self)
        
        if len(server._getAccounts()) > 0:
            self.__joined_accounts.extend(server._getAccounts())
            if self.__consensus == ConsensusMechanism.POA and server.isStartMiner():
                self.__joined_signer_accounts.append(server._getAccounts()[0])

        if self.__consensus == ConsensusMechanism.POS and server.isValidatorAtGenesis():
            self.__validator_ids.append(str(server.getId()))
        
        server.generateGethStartCommand()

        if self.__eth_service.isSave():
            save_path = self.__eth_service.getSavePath()
            node.addSharedFolder('/root/.ethereum', '../{}/{}/{}/ethereum'.format(save_path, self.__chain_name, server.getId()))
            node.addSharedFolder('/root/.ethash', '../{}/{}/{}/ethash'.format(save_path, self.__chain_name, server.getId()))
            makedirs('{}/{}/{}/ethereum'.format(save_path, self.__chain_name, server.getId()))
            makedirs('{}/{}/{}/ethash'.format(save_path, self.__chain_name, server.getId()))

    def configure(self, emulator:Emulator, pending_targets:Dict[str, Server]):
        for vnode in self.__pending_targets:
            node = emulator.getBindingFor(vnode)
            server = pending_targets[vnode]
            if self.__consensus == ConsensusMechanism.POS and server.isBootNode():
                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
                addr = str(ifaces[0].getAddress())
                bootnode_ip = self.getBootNodes()[0].split(":")[0]
                if addr == bootnode_ip:
                    validator_count = len(self.getValidatorIds())
                    index = self.__joined_accounts.index(server._getAccounts()[0])
                    self.__joined_accounts[index].setAllocBalance(balance=32*pow(10,18)*(validator_count+1))
        
        if self.__consensus == ConsensusMechanism.POA:
            self.__genesis.allocateBalance(self.getAllAccounts())
            self.__genesis.setSigner(self.getAllSignerAccounts())
    
    def getBootNodes(self) -> List[str]:
        """
        @brief get bootnode IPs.
        @returns list of IP addresses.
        """
        return self.__boot_node_addresses

    def getAllAccounts(self) -> List[EthAccount]:
        """
        @brief Get a joined list of all the created accounts on all nodes
        
        @returns list of EthAccount
        """
        return self.__joined_accounts

    def getAllSignerAccounts(self) -> List[EthAccount]:
        return self.__joined_signer_accounts

    def getValidatorIds(self) -> List[str]:
        return self.__validator_ids

    def getBeaconSetupNodeIp(self) -> str:
        return self.__beacon_setup_node_address

    def setGenesis(self, genesis:str) -> EthereumServer:
        """
        @brief set custom genesis
        
        @returns self, for chaining API calls.
        """
        self.__genesis.setGenesis(genesis)

        return self

    def getGenesis(self) -> Genesis:
        return self.__genesis

    def setConsensusMechanism(self, consensusMechanism:ConsensusMechanism) -> EthereumServer:
        '''
        @brief set ConsensusMechanism

        @param consensusMechanism supports POW and POA.

        @returns self, for chaining API calls. 
        '''
        self.__consensus = consensusMechanism
        self.__genesis = Genesis(self.__consensus)
        
        return self

    def getConsensusMechanism(self) -> ConsensusMechanism:

        return self.__consensus
    
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

    def setGasLimitPerBlock(self, gasLimit:int):
        """!
        @brief set GasLimit at Genesis 
        (the limit of gas cost per block)

        @param int
        
        @returns self, for chaining API calls
        """
        self.__genesis.setGasLimit(gasLimit)
        return self

    def setChainId(self, chainId:int):
        """!
        @brief set network Id at Genesit

        @param int

        @returns self, for chaining API calls
        """

        self.__chain_id = chainId
        self.__genesis.setChainId(self.__chain_id)
        return self

    def createNode(self, vnode: str) -> EthereumServer:
        eth = self.__eth_service
        self.__pending_targets.append(vnode)
        return eth.install(vnode, self)
    
    def addExternalAccount(self, address: str, balance: int) -> Blockchain:
        """!
        @brief allocate balance to an external account by setting alloc field of genesis file.

        @param address : external account's address to allocate balance

        @param balance

        @returns self, for chaining calls.
        """

        self.__genesis.addExternalAccount(address, balance)
        
        return self

    def getChainName(self) -> str:
        return self.__chain_name

    def getChainId(self) -> int:
        return self.__chain_id


    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
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


    __serial: int

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
        self.__save_state = saveState
        self.__save_path = savePath
        self.__override = override
        self.__blockchains = {}
        

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
            blockchain.configure(emulator, self._pending_targets)
        
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

    # def install(self, vnode: str, blockchain: Blockchain) -> Server:
    #     """!
    #     @brief install the service on a node identified by given name.
    #     """
    #     if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

    #     s = self._createServer(blockchain)
    #     self._pending_targets[vnode] = s

    #     return self._pending_targets[vnode]

    def install(self, vnode: str, *args) -> Server:
        """!
        @brief install the service on a node identified by given name.
        """
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]
        if len(args) == 0:
            s = self._createServer()
        elif len(args) == 1:
            blockchain = args[0]
            s = self._createServer(blockchain)
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]

    def createBlockchain(self, chainName:str, consensus: ConsensusMechanism):
        blockchain = Blockchain(self, chainName, consensus)
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
