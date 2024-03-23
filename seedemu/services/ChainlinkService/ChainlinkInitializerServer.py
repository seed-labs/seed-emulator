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
    __deploymentType: str
    __owner: str
    __rpcURL: str
    __privateKey: str
    __chain_id: int = 1337
    __rpc_port: int = 8545
    __number_of_oracle_contracts: int = 1
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator

    def installInitializer(self, node: Node):
        """
        @brief Install the service.
        """
        self.__installInitSoftware()
        if self.__deploymentType == "web3":
            # Deploy the contracts using web3
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
    
    def setContractOwner(self, owner: str):
        """
        @brief Set the owner of the contracts
        
        @param owner The owner of the contracts
        """
        self.__owner = owner

    def setDeploymentType(self, deploymentType: str = "web3"):
        """
        @brief Set the deployment type.
        
        @param deploymentType The deployment type.
        """
        self.__deploymentType = deploymentType
            
    def setOwnerPrivateKey(self, privateKey: str):
        """
        @brief Set the owner private key.
        
        @param privateKey The private key of the owner.
        """
        self.__privateKey = privateKey
        
    def setRPCbyUrl(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address or hostname for the chainlink node
        """
        self.__rpcURL = address
        
    def setRPCbyEthNodeName(self, vnode:str):
        """
        @brief Set the ethereum RPC address.

        @param vnode The name of the ethereum node
        """
        self.__vnode_name=vnode
        
    def setNumberOfOracleContracts(self, number_of_contracts: int):
        """
        @brief Set the number of oracle contracts.
        
        @param number_of_contracts The number of oracle contracts
        """
        self.__number_of_oracle_contracts = number_of_contracts
        
    def getIPbyEthNodeName(self, vnode:str):
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
        self.__rpcURL=address
        
    def __deployThroughWeb3(self):
        """
        @brief Deploy the contracts using web3.
        """
        # Deploy the contracts using web3
        self.__node.setFile('/contracts/deploy_linktoken_contract.py', LinkTokenDeploymentTemplate['link_token_contract'].format(rpc_url = self.__rpcURL, private_key = self.__privateKey, rpc_port = self.__rpc_port))
        self.__node.setFile('/contracts/link_token.abi', LinkTokenDeploymentTemplate['link_token_abi'])
        self.__node.setFile('/contracts/link_token.bin', LinkTokenDeploymentTemplate['link_token_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_linktoken_contract.py')
        self.__node.appendStartCommand('echo "LinkToken contract deployed"')
        self.__node.setFile('/contracts/deploy_oracle_contract.py', OracleContractDeploymentTemplate['oracle_contract_deploy'].format(rpc_url = self.__rpcURL, private_key = self.__privateKey, owner_address = self.__owner, rpc_port = self.__rpc_port, number_of_contracts=self.__number_of_oracle_contracts))
        self.__node.setFile('/contracts/oracle_contract.abi', OracleContractDeploymentTemplate['oracle_contract_abi'])
        self.__node.setFile('/contracts/oracle_contract.bin', OracleContractDeploymentTemplate['oracle_contract_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_oracle_contract.py')
        self.__node.appendStartCommand('echo "Oracle contract deployed"')
        
    def __webServer(self):
        # self.__node.appendStartCommand('oracle_contract_address=$(cat /deployed_contracts/oracle_contract_address.txt)')
        # self.__node.appendStartCommand('link_token_address=$(cat /deployed_contracts/link_token_address.txt)')
        # self.__node.addSoftware('nginx-light')
        # self.__node.addBuildCommand('pip3 install Flask')
        # self.__node.setFile("/flask_app.py", ChainlinkFileTemplate['flask_app'].format(rpc_url=self.__rpcURL, private_key=self.__privateKey, chain_id=self.__chain_id, rpc_port=self.__rpc_port))
        # self.__node.appendStartCommand('python3 /flask_app.py &')
        # self.__node.appendStartCommand("oracle_addresses=$(cat /deployed_contracts/oracle_contract_address.txt)")
        # self.__node.appendStartCommand("formatted_addresses=''; IFS=$'\\n'; for address in $oracle_addresses; do formatted_addresses+=\"<h1>Oracle Contracts: $address</h1><br>\"; done")
        # self.__node.setFile('/var/www/html/index_template.html', '<h1>Oracle Contract: {{oracleContractAddress}}</h1><h1>Link Token Contract: {{linkTokenAddress}}</h1>')
        # self.__node.appendStartCommand("cp /var/www/html/index_template.html /var/www/html/index.html")  # Copy template to the actual file
        # self.__node.appendStartCommand("sed -i 's|{{formatted_addresses}}|'$formatted_addresses'|g' /var/www/html/index.html")
        # self.__node.appendStartCommand("sed -i 's|{{link_token_address}}|'$link_token_address'|g' /var/www/html/index.html")
        # self.__node.appendStartCommand('sed -e "s/{{oracleContractAddress}}/${oracle_contract_address}/g" -e "s/{{linkTokenAddress}}/${link_token_address}/g" /var/www/html/index_template.html > /var/www/html/index.html')
        # self.__node.setFile('/etc/nginx/sites-available/default', ChainlinkFileTemplate['nginx_site'].format(port=80))
        # self.__node.appendStartCommand('service nginx start')
        self.__node.appendStartCommand('export link_token_address=$(cat /deployed_contracts/link_token_address.txt)')

        self.__node.addSoftware('nginx-light')
        self.__node.addBuildCommand('pip3 install Flask')

        self.__node.setFile("/flask_app.py", ChainlinkFileTemplate['flask_app'].format(
            rpc_url=self.__rpcURL, 
            private_key=self.__privateKey, 
            chain_id=self.__chain_id, 
            rpc_port=self.__rpc_port))
        self.__node.appendStartCommand('python3 /flask_app.py &')

        self.__node.appendStartCommand('''export oracle_addresses=$(cat /deployed_contracts/oracle_contract_address.txt)
        formatted_addresses="";
        IFS=$'\\n'; 
        for address in $oracle_addresses; do 
            formatted_addresses+="<h1>Oracle Contract: $address</h1><br>"; 
        done''')

        self.__node.setFile('/var/www/html/index_template.html', 
                            '<div>{{formatted_addresses}}</div><h1>Link Token Contract: {{linkTokenAddress}}</h1>')

        self.__node.appendStartCommand('''cp /var/www/html/index_template.html /var/www/html/index.html
        sed -i 's|{{formatted_addresses}}|'"$formatted_addresses"'|g' /var/www/html/index.html
        sed -i 's|{{linkTokenAddress}}|'"$link_token_address"'|g' /var/www/html/index.html''')

        self.__node.setFile('/etc/nginx/sites-available/default', ChainlinkFileTemplate['nginx_site'].format(port=80))
        self.__node.appendStartCommand('service nginx restart')

        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink Initilizer server object.\n'
        return out