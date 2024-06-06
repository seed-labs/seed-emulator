from __future__ import annotations
from seedemu.core import Node, Server
from seedemu.services.EthereumService import *
from .EthTemplates import EthServerFileTemplates 
from seedemu.services.EthereumService import *
import json
import os


class EthUtilityServer(Server):
    """!
    @brief The EthUtilityServer class.
    """

    DIR_PREFIX = '/utility_server'
    
    __blockchain:Blockchain
    __port: int
    __eth_node_url: str
    __linked_eth_node:str
    __chain_id: int

    def __init__(self, blockchain:Blockchain, port:int, linked_eth_node:str, 
                       linked_faucet_node:str):
        """!
        @brief constructor.
        """
        super().__init__()
        self.__blockchain = blockchain
        self.__linked_eth_node = linked_eth_node
        self.__linked_faucet_node = linked_faucet_node
        self.__chain_id = blockchain.getChainId()
        self.__eth_node_url = ''
        self.__eth_node_port = None
        self.__faucet_url = ''
        self.__faucet_port = None
        self.__contract_to_deploy = {}
        self.__contract_to_deploy_container_path = {}
        self.__contract_to_deploy_content = {}
        self.__port = port

    def setEthServerInfo(self, vnodeName:str, port:int):
        self.__linked_eth_node = vnodeName
        self.__eth_node_port = port
        return self
    
    def getLinkedEthNodeName(self) -> str:
        return self.__linked_eth_node
    
    def setFaucetServerInfo(self, vnodeName:str, port:int):
        self.__linked_faucet_node = vnodeName
        self.__faucet_port = port
        return self
    
    def getLinkedFaucetNodeName(self) -> str:
        return self.__linked_faucet_node
    
    def setPort(self, port: int):
        """!
        @brief Set HTTP port.

        @param port port.

        @returns self, for chaining API calls.
        """
        self.__port = port

        return self
    
    def getPort(self) -> int:
        return self.__port
        

    def setEthServerUrl(self, url):
        self.__eth_node_url = url
        return self
    
    def getEthNodeUrl(self):
        return self.__eth_node_url
    
    def setEthServerPort(self, port):
        self.__eth_node_port = port
        return self
    
    def setFaucetUrl(self, url):
        self.__faucet_url = url
        return self
    
    def setFaucetPort(self, port):
        self.__faucet_port = port
        return self
    
    def deployContractByFilePath(self, contract_name, abi_path, bin_path):
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
            'abi_path': self.DIR_PREFIX + f"/contracts/{contract_name}.abi",
            'bin_path': self.DIR_PREFIX + f"/contracts/{contract_name}.bin"
        }
    
    def deployContractByContent(self, contract_name, abi_content, bin_content):
        self.__contract_to_deploy_content[contract_name] = {
            'abi_content': abi_content,
            'bin_content': bin_content
        }
        self.__contract_to_deploy_container_path[contract_name] = {
            'abi_path': self.DIR_PREFIX + f"/contracts/{contract_name}.abi",
            'bin_path': self.DIR_PREFIX + f"/contracts/{contract_name}.bin"
        }
    
    def getBlockchain(self):
        return self.__blockchain
            
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("EthUtilityServer")

        node.addSoftware('python3 python3-pip')        
        node.addBuildCommand('pip3 install flask web3==5.31.1')

        self._installScriptFile(node)

        node.appendStartCommand('python3 {}/utility_server.py &'.format(self.DIR_PREFIX))
        node.appendStartCommand('bash {}/utility_server_setup.sh &'.format(self.DIR_PREFIX))


    def _installScriptFile(self, node: Node):
        """!
        @brief Install the script files.
        """

        for contract_name, path in self.__contract_to_deploy.items():
            node.importFile(hostpath=path['abi_path'], 
                   containerpath=self.__contract_to_deploy_container_path[contract_name]['abi_path'])
            node.importFile(hostpath=path['bin_path'], 
                   containerpath=self.__contract_to_deploy_container_path[contract_name]['bin_path'])
            
        for contract_name, value in self.__contract_to_deploy_content.items():
            node.setFile(self.__contract_to_deploy_container_path[contract_name]['abi_path'],
                         value['abi_content'])
            node.setFile(self.__contract_to_deploy_container_path[contract_name]['bin_path'],
                         value['bin_content'])
            
        node.setFile(self.DIR_PREFIX + '/contracts/contract_file_paths.txt', 
                     json.dumps(self.__contract_to_deploy_container_path))

        node.setFile(self.DIR_PREFIX + '/utility_server_setup.sh', 
                     UtilityServerFileTemplates['server_setup'])

        node.setFile(self.DIR_PREFIX + '/fund_account.py', 
                     UtilityServerFileTemplates['fund_account'].format(
            rpc_url     = self.__eth_node_url,
            rpc_port    = self.__eth_node_port,
            faucet_url  = self.__faucet_url,
            faucet_port = self.__faucet_port,
            dir_prefix  = self.DIR_PREFIX
        ))

        node.setFile(self.DIR_PREFIX + '/deploy_contract.py', 
                     UtilityServerFileTemplates['deploy_contract'].format(
            rpc_url    = self.__eth_node_url,
            rpc_port   = self.__eth_node_port,
            chain_id   = self.__chain_id,
            dir_prefix = self.DIR_PREFIX
        ))

        node.setFile(self.DIR_PREFIX  + '/utility_server.py', 
            UtilityServerFileTemplates['utility_server'].format(
                     port=self.__port, 
                     dir_prefix=self.DIR_PREFIX))

        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'EthUtilityServer object.\n'

        return out
