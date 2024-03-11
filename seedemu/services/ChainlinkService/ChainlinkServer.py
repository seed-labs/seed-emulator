from seedemu import *
from typing import Dict
from seedemu.core.Node import Node

from seedemu.core.Service import Server
from enum import Enum
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService import ChainlinkServerCommands
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
        ChainlinkServerCommands().installSoftware(node)
        
        if self.__vnode_name is not None:
            self.getIPbyEthNodeName(self.__vnode_name)
        
        if self.__eth_node_ip_address is None:
            raise Exception('RPC address not set')
        
        ChainlinkServerCommands().setConfigurationFiles(node, self.__eth_node_ip_address, self.__username, self.__password)
        ChainlinkServerCommands().chainlinkStartCommands(node)
        
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
        self.__eth_node_ip_address=address
          
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out
