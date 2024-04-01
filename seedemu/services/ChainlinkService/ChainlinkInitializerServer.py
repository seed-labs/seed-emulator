from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
import re
from seedemu.services.WebService import WebServerFileTemplates

class ChainlinkInitializerServer(Server):
    """
    @brief The Chainlink initializer class.
    """
    __node: Node
    __emulator: Emulator
    __deploymentType: str = "web3"
    __owner: str
    __rpc_url: str
    __owner_private_key: str
    __chain_id: int = 1337
    __rpc_port: int = 8545
    __rpc_vnode_name: str = None
    __faucet_vnode_name: str = None
    __faucet_url: str
    __faucet_port: int
    __server_port: int = 5000
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        # self.__faucet_util = FaucetUtil()
        
    # def setFaucetServerInfo(self, vnode: str, port = 80):
    #      """
    #         @brief Set the faucet server information.
    #      """

    #      self.__faucet_vnode_name = vnode
    #      self.__faucet_port = port

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator
        # self.__faucet_util.setFaucetServerInfo(vnode=self.__faucet_vnode_name, port=self.__faucet_port)
        # self.__faucet_util.configure(emulator)

    def installInitializer(self, node: Node):
        """
        @brief Install the service.
        """
        self.__installInitSoftware()
        if self.__rpc_vnode_name is not None:
            self.__rpc_url = self.__getIPbyEthNodeName(self.__rpc_vnode_name)
        
        if self.__rpc_url is None:
            raise Exception('RPC address not set')
        
        if self.__deploymentType == "web3":
            # Deploy the link contract using web3
            self.__deployThroughWeb3()
            
        self.__webServer()
    
    def __installInitSoftware(self):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            self.__node.addSoftware(software)
        self.__node.addBuildCommand('pip3 install web3==5.31.1')

    def setDeploymentType(self, deploymentType: str = "web3"):
        """
        @brief Set the deployment type.
        
        @param deploymentType The deployment type.
        """
        self.__deploymentType = deploymentType
        
    def setRPCbyUrl(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address or hostname for the chainlink node
        """
        self.__rpc_url = address
        
    def setRPCbyEthNodeName(self, vnode:str):
        """
        @brief Set the ethereum RPC address.

        @param vnode The name of the ethereum node
        """
        self.__rpc_vnode_name=vnode
        
    def setFaucetUrl(self, address: str, port: int):
        """
        @brief Set the faucet URL
        
        @param address The faucet URL
        @param port The faucet port
        """
        self.__faucet_url = address
        self.__faucet_port = port
        
        
    def __deployThroughWeb3(self):
        """
        @brief Deploy the contracts using web3.
        """
        # Deploy the contracts using web3
        self.__node.setFile('/contracts/deploy_linktoken_contract.py', LinkTokenDeploymentTemplate['link_token_contract'].format(rpc_url = self.__rpc_url, rpc_port = self.__rpc_port, faucet_url=self.__faucet_url, faucet_port=self.__faucet_port, chain_id=self.__chain_id))
        self.__node.setFile('/contracts/link_token.abi', LinkTokenDeploymentTemplate['link_token_abi'])
        self.__node.setFile('/contracts/link_token.bin', LinkTokenDeploymentTemplate['link_token_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_linktoken_contract.py')
        self.__node.appendStartCommand('echo "LinkToken contract deployed"')
        
    def __webServer(self):
        self.__node.appendStartCommand('export link_token_address=$(cat /deployed_contracts/link_token_address.txt)')
        self.__node.addSoftware('nginx-light')
        self.__node.addBuildCommand('pip3 install Flask')
        self.__node.setFile("/flask_app.py", ChainlinkFileTemplate['flask_app'].format(rpc_url=self.__rpc_url, rpc_port=self.__rpc_port, port=self.__server_port))
        self.__node.appendStartCommand('python3 /flask_app.py &')
        self.__node.setFile('/var/www/html/index_template.html', 
                            '<h1>Link Token Contract: {{linkTokenAddress}}</h1>')
        self.__node.appendStartCommand('''cp /var/www/html/index_template.html /var/www/html/index.html
        sed -i 's|{{linkTokenAddress}}|'"$link_token_address"'|g' /var/www/html/index.html''')
        self.__node.setFile('/etc/nginx/sites-available/default', ChainlinkFileTemplate['nginx_site'].format(port=80))
        self.__node.appendStartCommand('service nginx restart')

    def setOwner(self, owner: str, owner_private_key: str):
        """
        @brief Set the owner of the contracts
        
        @param owner The owner of the contracts
        @param owner_private_key The private key of the owner.
        """
        self.__owner = owner
        self.__owner_private_key = owner_private_key
    
    def __getIPbyEthNodeName(self, vnode:str):
        """
        @brief Get the IP address of the ethereum node.
        
        @param vnode The name of the ethereum node
        """
        node = self.__emulator.getBindingFor(vnode)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        return address
    
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink Initilizer server object.\n'
        return out