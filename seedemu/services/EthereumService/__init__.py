#!/usr/bin/env python
# encoding: utf-8
# __author__ = 'Demon'

from __future__ import annotations
from .EthTemplates import *
from .EthEnum import ConsensusMechanism, Syncmode, EthereumServerTypes
from .EthUtil import Genesis, EthAccount, SmartContract
from .EthereumServer import *

from os import mkdir, path, makedirs, rename
from seedemu.core import Node, Service, Server, Emulator
from typing import Dict, List

class EthereumService(Service):
    """!
    @brief The Ethereum network service.
    This service allows one to run a private Ethereum network in the emulator.
    """

    __serial: int
    __boot_node_addresses: Dict[ConsensusMechanism, List[str]]
    __joined_accounts: List[EthAccount]
    __joined_signer_accounts: List[EthAccount]
    __validator_ids: List[str]
    __beacon_setup_node_address: str

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
        self.__validator_ids = []
        self.__beacon_setup_node_address = ''

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

    def getValidatorIds(self) -> List[str]:
        return self.__validator_ids

    def getBeaconSetupNodeIp(self) -> str:
        return self.__beacon_setup_node_address

    def _doConfigure(self, node: Node, server: EthereumServer):
        self._log('configuring as{}/{} as an eth node...'.format(node.getAsn(), node.getName()))

        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
        addr = '{}:{}'.format(str(ifaces[0].getAddress()), server.getBootNodeHttpPort())
        
        if server.isBootNode():
            self._log('adding as{}/{} as consensus-{} bootnode...'.format(node.getAsn(), node.getName(), server.getConsensusMechanism().value))
            self.__boot_node_addresses[server.getConsensusMechanism()].append(addr)

        if server.isBeaconSetupNode():
            self.__beacon_setup_node_address = '{}:{}'.format(ifaces[0].getAddress(), server.getBeaconSetupHttpPort())

        server._createAccounts(self)
        
        if len(server._getAccounts()) > 0:
            self.__joined_accounts.extend(server._getAccounts())
            if server.getConsensusMechanism() == ConsensusMechanism.POA and server.isStartMiner():
                self.__joined_signer_accounts.append(server._getAccounts()[0])

        if server.isValidatorAtGenesis():
            self.__validator_ids.append(str(server.getId()))
            
        if self.__save_state:
            node.addSharedFolder('/root/.ethereum', '../{}/{}/ethereum'.format(self.__save_path, server.getId()))
            node.addSharedFolder('/root/.ethash', '../{}/{}/ethash'.format(self.__save_path, server.getId()))
            makedirs('{}/{}/ethereum'.format(self.__save_path, server.getId()))
            makedirs('{}/{}/ethash'.format(self.__save_path, server.getId()))
    
    def configure(self, emulator: Emulator):
        if self.__save_state:
            self._createSharedFolder()
        super().configure(emulator)
        for (vnode, server) in self._pending_targets.items():
            node = emulator.getBindingFor(vnode)
            if server.isBootNode() and server.isPoSEnabled():
                ifaces = node.getInterfaces()
                assert len(ifaces) > 0, 'EthereumService::_doConfigure(): node as{}/{} has not interfaces'.format()
                addr = str(ifaces[0].getAddress())
                bootnode_ip = self.getBootNodes(server.getConsensusMechanism())[0].split(":")[0]
                if addr == bootnode_ip:
                    validator_count = len(self.getValidatorIds())
                    index = self.__joined_accounts.index(server._getAccounts()[0])
                    self.__joined_accounts[index].setAllocBalance(balance=32*pow(10,18)*(validator_count+1))
        
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

    def install(self, vnode: str) -> Server:
        """!
        @brief install the service on a node identified by given name.
        """
        if vnode in self._pending_targets.keys(): return self._pending_targets[vnode]

        s = self._createServer()
        self._pending_targets[vnode] = s

        return self._pending_targets[vnode]

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
