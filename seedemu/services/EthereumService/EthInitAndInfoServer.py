from __future__ import annotations
from seedemu.core import Node, Server
from seedemu.services.EthereumService import *
from .EthTemplates import EthInitializerTemplate
from seedemu.services.EthereumService import *
import json
import os


class EthInitAndInfoServer(Server):
    """!
    @brief The FaucetServer class.
    """
    
    __blockchain:Blockchain
    __port: int
    __rpc_url: str
    __linked_eth_node:str
    __chain_id: int

    def __init__(self, blockchain:Blockchain):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        self.__blockchain = blockchain
        self.__linked_eth_node = None
        self.__linked_faucet_node = None
        self.__chain_id = blockchain.getChainId()
        self.__rpc_url = ''
        self.__rpc_port = None
        self.__faucet_url = ''
        self.__faucet_port = None
        self.__contract_to_deploy = {}
        self.__contract_to_deploy_container_path = {}
        self.__port = 5000

    def setLinkedEthNode(self, vnodeName:str):
        self.__linked_eth_node = vnodeName
        return self
    
    def getLinkedEthNodeName(self) -> str:
        return self.__linked_eth_node
    
    def setLinkedFaucetNode(self, vnodeName:str):
        self.__linked_faucet_node = vnodeName
        return self
    
    def getLinkedFaucetNodeName(self) -> str:
        return self.__linked_faucet_node
    
    def setPort(self, port: int) -> FaucetServer:
        """!
        @brief Set HTTP port.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self

    def setRpcUrl(self, url):
        self.__rpc_url = url
        return self
    
    def getRpcUrl(self):
        return self.__rpc_url
    
    def setRpcPort(self, port):
        self.__rpc_port = port
        return self
    
    def setFaucetUrl(self, url):
        self.__faucet_url = url
        return self
    
    def setFaucetPort(self, port):
        self.__faucet_port = port
        return self
    
    def deployContract(self, contract_name, abi_path, bin_path):
        if not os.path.isabs(abi_path):
            base_dir = os.getcwd()
        
            # Join the base directory and the relative path to get the absolute path
            abi_path = os.path.abspath(os.path.join(base_dir, abi_path))

        if not os.path.isabs(bin_path):
            base_dir = os.getcwd()
        
            # Join the base directory and the relative path to get the absolute path
            bin_path = os.path.abspath(os.path.join(base_dir, bin_path))

        self.__contract_to_deploy[contract_name] = {
            'abi_path': abi_path,
            'bin_path': bin_path
        }
        self.__contract_to_deploy_container_path[contract_name] = {
            'abi_path': f"/contracts/{abi_path.split('/')[-1]}",
            'bin_path': f"/contracts/{bin_path.split('/')[-1]}"
        }
    
    def getBlockchain(self):
        return self.__blockchain
            
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("EthInitAndInfoServer")

        node.addSoftware('python3 python3-pip')        
        node.addBuildCommand('pip3 install flask web3==5.31.1')
        for contract_name, path in self.__contract_to_deploy.items():
            node.importFile(hostpath=path['abi_path'], 
                            containerpath=self.__contract_to_deploy_container_path[contract_name]['abi_path'])
            node.importFile(hostpath=path['bin_path'], 
                            containerpath=self.__contract_to_deploy_container_path[contract_name]['bin_path'])
            
        node.setFile('/contracts/contract_file_paths.txt', json.dumps(self.__contract_to_deploy_container_path))
        node.setFile('/fund_account.py', EthInitializerTemplate['fund_account'].format(
            rpc_url = self.__rpc_url,
            rpc_port = self.__rpc_port,
            faucet_url = self.__faucet_url,
            faucet_port = self.__faucet_port
        ))
        node.setFile('/deploy_contract.py', EthInitializerTemplate['contract_deploy'].format(
            rpc_url = self.__rpc_url,
            rpc_port = self.__rpc_port,
            chain_id = self.__chain_id
        ))

        node.setFile('/info_server.py', EthInitializerTemplate['info_server'].format(port=self.__port))
        node.appendStartCommand('python3 /info_server.py &')
        node.appendStartCommand('python3 /fund_account.py')
        node.appendStartCommand('python3 /deploy_contract.py')
        

        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EthInitializer server object.\n'

        return out
