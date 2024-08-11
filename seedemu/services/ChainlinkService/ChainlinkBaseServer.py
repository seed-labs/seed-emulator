from seedemu import *
from seedemu.core.Node import Node
from seedemu.core.Service import Server
from seedemu.core.enums import NetworkType
from .ChainlinkTemplates import *
import re

class ChainlinkBaseServer(Server):
    """
    @brief The Chainlink base server. It serves as a base class 
           for two types of Chainlink nodes 
    """
    _chain_id: int

    _eth_server_ip: str
    _eth_server_ws_port: int
    _eth_server_http_port: int

    _util_server_ip: str
    _util_server_port: int

    _faucet_server_ip:str
    _faucet_server_port: int

    def __init__(self):
        """
        @brief Constructor.
        """
        super().__init__()


    def _setEthServer(self, eth_server_ip:str, 
                            eth_server_http_port:int = 8545 , 
                            eth_server_ws_port:int = 8546, 
                            chain_id:int = 1337):
        self._eth_server_ip        = eth_server_ip
        self._eth_server_http_port = eth_server_http_port
        self._eth_server_ws_port   = eth_server_ws_port
        self._chain_id             = chain_id
        return self


    def _setUtilityServer(self, util_server_ip:str, 
                                util_server_port:int):
        self._util_server_ip   = util_server_ip
        self._util_server_port = util_server_port
        return self


    def _setFaucetServer(self, faucet_server_ip:str, 
                               faucet_server_port:int):
        self._faucet_server_ip   = faucet_server_ip
        self._faucet_server_port = faucet_server_port
        return self

