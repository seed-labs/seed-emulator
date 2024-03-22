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
    __eth_node_ip_address: str
    __vnode_name: str = None
    __username: str = "seed@seed.com"
    __password: str = "Seed@emulator123"
    __database_node_ip: str
    __database_username: str
    __database_password: str
    __init_node_url: str
    
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
        
        if self.__vnode_name is not None:
            self.__getIPbyEthNodeName(self.__vnode_name)
        
        if self.__eth_node_ip_address is None:
            raise Exception('RPC address not set')
        
        self.__setConfigurationFiles()
        self.__chainlinkStartCommands()
        self.__configureJobs()
        self.__node.appendStartCommand('tail -f chainlink_logs.txt')
        
    def __configureJobs(self):
        self.__node.appendStartCommand(ChainlinkFileTemplate['check_init_node'].format(init_node_url=self.__init_node_url))
        self.__node.appendStartCommand(ChainlinkFileTemplate['get_oracle_contract_address'].format(init_node_url=self.__init_node_url))
        self.__node.appendStartCommand(ChainlinkFileTemplate['create_jobs'])
        
    def __installSoftware(self):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib']
        for software in software_list:
            self.__node.addSoftware(software)
            
    def __setConfigurationFiles(self):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(ip_address=self.__eth_node_ip_address)
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
        
    def setInitNodeUrl(self, url: str):
        """
        @brief Set the chainlink init node
        """
        self.__init_node_url = url
                
    def setRPCbyUrl(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address or hostname for the chainlink node
        """
        self.__eth_node_ip_address = address
        
    def setRPCbyEthNodeName(self, vnode:str):
        """
        @brief Set the ethereum RPC address.

        @param vnode The name of the ethereum node
        """
        self.__vnode_name=vnode
    
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
    
    def setDatabaseNode(self, ip: str, username: str, password: str):
        """
        @brief Set the database node.
        """
        # Set the database node ip, username and password
        self.__database_node_ip = ip
        self.__database_username = username
        self.__database_password = password
    
    def __getFaucet(self):
        # Get Faucet address from the Database Node using database query
        self.__node.appendStartCommand()
        self.__node.appendStartCommand("chainlink admin login -f /api.txt")
        self.__node.appendStartCommand("chainlink keys eth create > /tmp/eth_key")
        
        
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
        self.__eth_node_ip_address=address
          
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out
