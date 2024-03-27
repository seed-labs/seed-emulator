from __future__ import annotations
from seedemu.core import Node, Service, Server
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType
from seedemu.services.EthereumService import *
from typing import Dict
from eth_account import Account
from eth_account.signers.local import LocalAccount
from os import path

FaucetServerFileTemplates: Dict[str, str] = {}
FaucetServerFileTemplates['fund_curl'] = "curl -X POST -d 'address={recipient}&amount={amount}' http://localhost:{port}/fundme"
FaucetServerFileTemplates['fund_script'] = '''\
#!/bin/bash

# Define the URL of the server to connect to
SERVER_URL="http://localhost:{port}"

# Number of attempts
ATTEMPTS=10

# Initialize a counter
count=0

# Loop until connection is successful or maximum attempts reached
while [ $count -lt $ATTEMPTS ]; do
    # Perform an HTTP GET request to the server and check the response status code
    status_code=$(curl -s -o /dev/null -w "%{{http_code}}" "$SERVER_URL")

    # Check if the server is accessible (HTTP status code 200)
    if [ "$status_code" -eq 200 ]; then
        echo "Connection successful."
        {fund_command}
        exit 0  # Exit with success status
    else
        echo "Attempt $((count+1)): Connection failed (HTTP status code $status_code). Retrying..."
        count=$((count+1))  # Increment the counter
        sleep 10  # Wait for 10 seconds before retrying
    fi
done

# If maximum attempts reached and connection is still unsuccessful
echo "Connection failed after $ATTEMPTS attempts."
exit 1  # Exit with error status
'''

FaucetServerFileTemplates['faucet_server'] = '''\
from flask import Flask, request
from web3 import Web3
from web3.middleware import geth_poa_middleware
import sys, time
from hexbytes import HexBytes

app = Flask(__name__)

# Connect to a geth node
def connect_to_geth(url, consensus):
  if   consensus==  'POA': 
        return connect_to_geth_poa(url)
  elif consensus == 'POS':
        return connect_to_geth_pos(url)
  elif consensus == 'POW':
        return connect_to_geth_pow(url)

# Connect to a geth node
def connect_to_geth_pos(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      return ""
   return web3

# Connect to a geth node
def connect_to_geth_poa(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      return ""
   web3.middleware_onion.inject(geth_poa_middleware, layer=0)
   return web3

# Connect to a geth node
def connect_to_geth_pow(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      return ""
   return web3

# Construct a transaction
def construct_raw_transaction(sender, recipient, nonce, amount, data):
   tx = {{
     'nonce': nonce,
     'from':  sender,
     'to':    HexBytes(recipient),
     'value': Web3.toWei(amount, 'ether'),
     'gas': 2000000,
     'chainId': {chain_id},  # Must match with the value used in the emulator
     'gasPrice': Web3.toWei('50', 'gwei'),
     'data':  data
    }}
   return tx

# Send raw transaction
def send_raw_transaction(web3, sender, sender_key, recipient, amount, data):
   print("---------Sending Raw Transaction ---------------")
   nonce  = web3.eth.getTransactionCount(sender)
   tx = construct_raw_transaction(sender, recipient, nonce, amount, data)
   signed_tx  = web3.eth.account.signTransaction(tx, sender_key)
   tx_hash    = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
   print("Transaction Hash: {{}}".format(tx_hash.hex()))

   tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
   print("Transaction Receipt: {{}}".format(tx_receipt))
   return tx_receipt

def create_account(web3:Web3):
    # Generate a new Ethereum account
    account = web3.eth.account.create()
    return account
    
trial = 5
while trial > 0:
    trial -= 1
    web3 = connect_to_geth('{rpc_url}', '{consensus}')
    if web3 == "":
        time.sleep(10)
    else:
        app.config['WEB3'] = web3
        break
    if trial == 0:
        sys.exit("Connection failed!")

app.config['SENDER_ADDRESS'] = "{account_address}"
app.config['SENDER_KEY'] = "{account_key}"

@app.route('/')
def index():
    return 'OK', 200

# Route for handling form submission
@app.route('/fundme', methods=['POST'])
def submit_form():
    recipient = request.form.get('address')
    amount = request.form.get('amount')
    tx_receipt = send_raw_transaction(app.config['WEB3'], app.config['SENDER_ADDRESS'], app.config['SENDER_KEY'], recipient, amount, '')
    api_response = {{'message': f'Funds successfully sent to {{recipient}} for amount {{amount}}.\\n{{tx_receipt}}'}}

    return api_response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port={port}, debug=True)

'''

class FaucetServer(Server):
    """!
    @brief The FaucetServer class.
    """
    
    __port: int
    __account: LocalAccount
    __balance: int
    __rpc_url: str
    __linked_eth_node:str
    __chain_id: int
    __consensus: ConsensusMechanism

    def __init__(self):
        """!
        @brief FaucetServer constructor.
        """
        super().__init__()
        self.__port = 80
        self.__account = Account.from_key('0xa9aec7f51b6b872d86676d4e5facf4ddf6850745af133b647781d008894fa3aa')
        self.__balance = 1000
        self.__balance_unit = EthUnit.ETHER
        self.__rpc_url = ''
        self.__linked_eth_node = ''
        self.__chain_id = -1
        self.__fundlist = []

    def linkEthNodeByName(self, nodename:str) -> FaucetServer:
        """!
        @brief Set Rpc By Eth node name.
        
        @param nodename vnodename.
        
        @returns self, for chaining API calls.
        """
        self.__linked_eth_node = nodename
        return self
    
    def getBalance(self):
        return self.__balance
    
    def getBalanceUnit(self):
        return self.__balance_unit
    
    def getAccount(self):
        return self.__account
    
    def getLinkedEthNodeName(self) -> str:
        return self.__linked_eth_node
    
    def importAccount(self, keyfilePath: str, password = "admin"):
        """
        @brief import account from keyfile.
        
        @param keyfilePath path of keyfile.

        @param password password of the keyfile.

        @returns self, for chaining API calls.
        """
        assert path.exists(keyfilePath), "EthAccount::__importAccount: keyFile does not exist. path : {}".format(keyfilePath)
        f = open(keyfilePath, "r")
        keyfileContent = f.read()
        f.close()
        
        self.__account = Account.from_key(Account.decrypt(keyfile_json=keyfileContent,password=password))
        return self

    def setAccountBalance(self, balance:int, unit:EthUnit=EthUnit.ETHER):
        """
        @brief set account balance by manual. (Default: 1000Eth).
        
        @param balance.

        @returns self, for chaining API calls.
        """
        self.__balance = balance
        self.__balance_unit = unit
        return self

    def fund(self, recipient, amount):
        self.__fundlist.append((recipient, amount))
        return self

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
        return
    
    def setChainId(self, chain_id):
        self.__chain_id = chain_id
        return
    
    def setConsensusMechanism(self, consensus):
        self.__consensus = consensus
    
    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.appendClassName("FaucetService")
        node.addSoftware('python3 python3-pip')
        
        node.addBuildCommand('pip3 install flask web3==5.31.1')
        # node.setFile('/var/www/html/index.html', self.__index.format(asn = node.getAsn(), nodeName = node.getName()))
        node.setFile('/app.py', FaucetServerFileTemplates['faucet_server'].format(chain_id=self.__chain_id,
                                                                                  rpc_url = self.__rpc_url, 
                                                                                  consensus= self.__consensus.value,
                                                                                  account_address = self.__account.address, 
                                                                                  account_key=self.__account.privateKey.hex(),
                                                                                  port=self.__port))
        node.appendStartCommand('python3 /app.py &')

        funds_list = []
        for recipient, amount in self.__fundlist:
            funds_list.append(FaucetServerFileTemplates['fund_curl'].format(recipient=recipient, 
                                                                            amount=amount,
                                                                            port = self.__port))
        node.setFile('/fund.sh', FaucetServerFileTemplates['fund_script'].format(port=self.__port,
                                                                                 fund_command=';'.join(funds_list)))
        node.appendStartCommand('chmod +x /fund.sh')
        node.appendStartCommand('/fund.sh')
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Web server object.\n'

        return out

class FaucetService(Service):
    """!
    @brief The FaucetService class.
    """
    __emulator:Emulator

    def __init__(self):
        """!
        @brief FaucetService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('EthereumService', True, False)

    def _createServer(self) -> Server:
        return FaucetServer()
    
    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        
        return super().configure(emulator)
        
    
    def _doConfigure(self, node: Node, server: Server):
        """!
        @brief configure the node. Some services may need to by configure before
        rendered.

        This is currently used by the DNS layer to configure NS and gules
        records before the actual installation.
        
        @param node node
        @param server server
        """

        server.__class__ = FaucetServer

        linked_eth_node_name = server.getLinkedEthNodeName()

        assert linked_eth_node_name != '', 'both rpc url and eth node are not set'
        server.setRpcUrl(f'http://{self.__getIpByVnodeName(linked_eth_node_name)}:8545')
        
        ethServer:EthereumServer = self.__emulator.getServerByVirtualNodeName(linked_eth_node_name)
        ethServer.importAccountFromKey(server.getAccount().privateKey.hex(), balance=server.getBalance(), unit=server.getBalanceUnit())
        
        server.setChainId(ethServer.getChainId())
        server.setConsensusMechanism(ethServer.getConsensusMechanism())
        return
    
    def getName(self) -> str:
        return 'FaucetService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'FaucetServiceLayer\n'

        return out
    
    def __getIpByVnodeName(self, nodename:str) -> str:
        node = self.__emulator.getBindingFor(nodename)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                return address