
from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.services.EthereumService import *
from .FaucetUtil import *

# This service is a base code of a service utilizing faucetServer.

FUND_SCRIPT = '''\
#!/bin/env python3

import time
import requests
import json
from eth_account import Account
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get("{faucet_url}")
        if response.status_code == 200:
            break
        time.sleep(10)
        if time.time() - start_time > timeout:
            logging.info("faucet server connection failed: 600 seconds exhausted.")
            exit()
    except Exception as e:
        pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_url = "{faucet_fund_url}"
	try:
		response = requests.post(request_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
		logging.info(response)
		if response.status_code == 200:
			api_response = response.json()
			message = api_response['message']
			if message:
				print(f"Success: {{message}}")
			else:
				logging.error("Funds request was successful but the response format is unexpected.")
		else:
			api_response = response.json()
			message = api_response['message']
			logging.error(f"Failed to request funds from faucet server. Status code: {{response.status_code}} Message: {{message}}")
			# Send another request
			logging.info("Sending another request to faucet server.")
			send_fundme_request(account_address)
	except Exception as e:
		logging.error(f"An error occurred: {{str(e)}}")
		exit()

# Create an account
user_account = Account.create()
account_address = user_account.address

# Send /fundme request to faucet server
send_fundme_request(account_address)
'''

class FaucetUserServer(Server):
    """!
    @brief The FaucetServer class.
    """
    __faucet_util:FaucetUtil
    __faucet_port: int
    __faucet_vnode_name:set
  
    def __init__(self):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        self.__faucet_util = FaucetUtil()

    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port
        
    def configure(self, emulator:Emulator):
        self.__faucet_util.setFaucetServerInfo(vnode=self.__faucet_vnode_name, port=self.__faucet_port)
        self.__faucet_util.configure(emulator)

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetUserService")
        node.addSoftware('python3 python3-pip')
        node.addBuildCommand('pip3 install eth_account==0.5.9 requests')
        node.setFile('/fund.py', FUND_SCRIPT.format(faucet_url=self.__faucet_util.getFacuetUrl(),
                                                    faucet_fund_url=self.__faucet_util.getFaucetFundUrl()))
        node.appendStartCommand('chmod +x /fund.py')
        node.appendStartCommand('/fund.py')

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Faucet user server object.\n'

        return out

class FaucetUserService(Service):
    """!
    @brief The FaucetUserService class.
    """
    __faucet_port: int
    __faucet_vnode_name:set
    
    def __init__(self):
        """!
        @brief FaucetUserService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def setFaucetServerInfo(self, vnode: str, port = 80):
        """
        @brief set account from key string.
        
        @param keyString key string.

        @param isEncrypted indicates if the keyString is encrypted or not.

        @param password password of the key.

        @returns self, for chaining API calls.
        """
        
        self.__faucet_vnode_name = vnode
        self.__faucet_port = port

    def _createServer(self) -> Server:
        return FaucetUserServer()
    
    def configure(self, emulator: Emulator):
        super().configure(emulator)

        for (server, node) in self.getTargets():
            server.setFaucetServerInfo(self.__faucet_vnode_name, self.__faucet_port)
            server.configure(emulator)
        return 
    
    
    def getName(self) -> str:
        return 'FaucetUserService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'FaucetUserServiceLayer\n'

        return out
    
