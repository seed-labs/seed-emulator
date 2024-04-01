from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
import re



class ChainlinkServer(Server):
    """
    @brief The Chainlink virtual node server.
    """
    __node: Node
    __emulator: Emulator
    __rpc_url: str
    __rpc_vnode_name: str = None
    __username: str = "seed@seed.com"
    __password: str = "Seed@emulator123"
    __init_node_name: str = None
    __init_node_url: str
    __flask_server_port: int = 5000
    __faucet_node_url: str
    __faucet_node_name: str = None
    __faucet_node_port: int
    __chain_id: int = 1337
    __rpc_ws_port: int = 8546
    __rpc_port: int = 8545
    __owner: str = None
    __owner_private_key: str = None
    
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK

    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator

    def install(self, node: Node):
        """
        @brief Install the service.
        """
        self.__installSoftware()
        
        if self.__rpc_vnode_name is not None:
            self.__rpc_url = self.__getIPbyEthNodeName(self.__rpc_vnode_name)
        
        if self.__rpc_url is None:
            raise Exception('RPC address not set')
        
        if self.__init_node_name is not None:
            self.__init_node_url = self.__getIPbyEthNodeName(self.__init_node_name)
            
        if self.__init_node_url is None:
            raise Exception('Init node url address not set')
        
        if self.__faucet_node_name is not None:
            self.__faucet_node_url = self.__getIPbyEthNodeName(self.__faucet_node_name)
        
        if self.__faucet_node_url is None:
            raise Exception('Faucet node url address not set')
        
        self.__setConfigurationFiles()
        self.__chainlinkStartCommands()
        self.__node.appendStartCommand(ChainlinkFileTemplate['send_get_eth_request'].format(faucet_server_url=self.__faucet_node_url, faucet_server_port=self.__faucet_node_port))
        self.__node.appendStartCommand(ChainlinkFileTemplate['check_init_node'].format(init_node_url=self.__init_node_url))
        self.__deploy_oracle_contract()
        self.__node.appendStartCommand(ChainlinkFileTemplate['send_flask_request'].format(init_node_url=self.__init_node_url, flask_server_port=self.__flask_server_port))
        self.__node.appendStartCommand(ChainlinkFileTemplate['create_jobs'])
        self.__node.appendStartCommand('tail -f chainlink_logs.txt')
        
    def __installSoftware(self):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            self.__node.addSoftware(software)
        self.__node.addBuildCommand('pip3 install web3==5.31.1')
            
    def __setConfigurationFiles(self):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(rpc_url=self.__rpc_url, chain_id=self.__chain_id, rpc_ws_port=self.__rpc_ws_port, rpc_port=self.__rpc_port)
        self.__node.setFile('/config.toml', config_content)
        self.__node.setFile('/secrets.toml', ChainlinkFileTemplate['secrets'])
        self.__node.setFile('/api.txt', ChainlinkFileTemplate['api'].format(username=self.__username, password=self.__password))
        self.__node.setFile('/jobs/getUint256.toml', ChainlinkJobsTemplate['getUint256'])
        self.__node.setFile('/jobs/getBool.toml', ChainlinkJobsTemplate['getBool'])
        
    def __chainlinkStartCommands(self):
        """
        @brief Add start commands.
        """        
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
nohup chainlink node -config /config.toml -secrets /secrets.toml start -api /api.txt > chainlink_logs.txt 2>&1 &
"""
        self.__node.appendStartCommand(start_commands)
    
    def __deploy_oracle_contract(self):
        """
        @brief Deploy the oracle contract.
        """
        self.__node.appendStartCommand(ChainlinkFileTemplate['save_sender_address'])
        self.__node.setFile('/contracts/deploy_oracle_contract.py', OracleContractDeploymentTemplate['oracle_contract_deploy'].format(rpc_url = self.__rpc_url, rpc_port = self.__rpc_port, init_node_url=self.__init_node_url, chain_id=self.__chain_id, faucet_url=self.__faucet_node_url, faucet_port=self.__faucet_node_port))
        self.__node.setFile('/contracts/oracle_contract.abi', OracleContractDeploymentTemplate['oracle_contract_abi'])
        self.__node.setFile('/contracts/oracle_contract.bin', OracleContractDeploymentTemplate['oracle_contract_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_oracle_contract.py')
        self.__node.appendStartCommand('echo "Oracle contract deployed and setAuthorizedSender set."')

    
    def __set_authorized_sender(self):
        """
        @brief Set the authorized sender.
        """
        self.__node.appendStartCommand(ChainlinkFileTemplate['save_sender_address'])
        self.__node.setFile('/contracts/setAuthorizedSender.py', ChainlinkFileTemplate['set_authorized_sender'].format(rpc_url = self.__rpc_url, private_key = self.__owner_private_key, chain_id = self.__chain_id, rpc_port = self.__rpc_port))
        self.__node.appendStartCommand('python3 ./contracts/setAuthorizedSender.py')
    
    def setInitNodeIP(self, init_node_name: str):
        """
        @brief Set the chainlink init node
        """
        self.__init_node_name = init_node_name
                
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
    
    def setUsernameAndPassword(self, username: str, password: str):
        """
        Set the username and password for the Chainlink node API after validating them.

        @param username: The username for the Chainlink node API.
        @param password: The password for the Chainlink node API.
        """
        if not self.__validate_username(username):
            raise ValueError("The username must be a valid email address.")
        if not self.__validate_password(password):
            raise ValueError("The password must be between 16 and 50 characters in length.")

        self.__username = username
        self.__password = password
        
    def __validate_username(self, username: str) -> bool:
        """
        Check if the username is a valid email address.
        """
        pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        return re.fullmatch(pattern, username) is not None
    
    def __validate_password(self, password: str) -> bool:
        """
        Check if the password length is between 16 and 50 characters.
        """
        return 16 <= len(password) <= 50
    
    def setFaucetUrl(self, faucet_node_url: str):
        """
        Set the faucet node for the Chainlink node API.

        @param faucet_node_url: The url of the faucet node.
        @param faucet_node_port: The port number of the faucet node.
        """
        self.__faucet_node_url = faucet_node_url
    
    def setFaucetPort(self, faucet_node_port: int):
        """
        Set the faucet port for the Chainlink node API.

        @param faucet_node_port: The port number of the faucet node.
        """
        self.__faucet_node_port = faucet_node_port
        
    def setFaucetNodeName(self, faucet_node_name: str):
        """
        Set the faucet node for the Chainlink node API.

        @param faucet_node_name: The name of the faucet node.
        """
        self.__faucet_node_name = faucet_node_name
        
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
        out += 'Chainlink server object.\n'
        return out
