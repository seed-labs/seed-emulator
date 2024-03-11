from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService.ChainlinkTemplates.ChainlinkFileTemplate import ChainlinkFileTemplate
from seedemu.services.ChainlinkService.ChainlinkTemplates import *

class ChainlinkServerCommands:
    def __init__(self):
        pass
    
    def installSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib']
        for software in software_list:
            node.addSoftware(software)
    
    def installInitSoftware(self, node: Node):
        """
        @brief Install the software.
        """
        software_list = ['curl', 'python3', 'python3-pip']
        for software in software_list:
            node.addSoftware(software)
        node.addBuildCommand('pip3 install web3==5.31.1')
        
    def setConfigurationFiles(self, node: Node, eth_node_ip_address: str, username: str, password: str):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(ip_address=eth_node_ip_address)
        node.setFile('/config.toml', config_content)
        node.setFile('/secrets.toml', ChainlinkFileTemplate['secrets'])
        node.setFile('/api.txt', ChainlinkFileTemplate['api'].format(username=username, password=password))
        
    def chainlinkStartCommands(self, node: Node):
        """
        @brief Add start commands.
        """
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
chainlink node -config /config.toml -secrets /secrets.toml start -api /api.txt
"""
        node.appendStartCommand(start_commands)
        