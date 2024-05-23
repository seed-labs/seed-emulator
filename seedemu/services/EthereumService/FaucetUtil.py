from typing import Dict
from seedemu.core import Configurable
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NetworkType



FaucetServerFileTemplates: Dict[str, str] = {}
FaucetServerFileTemplates['faucet_fund_url'] = "http://{address}:{port}/fundme"
FaucetServerFileTemplates['faucet_url'] = "http://{address}:{port}/"

FaucetServerFileTemplates['fund_curl'] = "curl -X POST -d 'address={recipient}&amount={amount}' http://{address}:{port}/fundme"
FaucetServerFileTemplates['fund_script'] = '''\
#!/bin/bash

# Define the URL of the server to connect to
SERVER_URL="http://{address}:{port}"

# Number of attempts
ATTEMPTS={max_attempts}

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
from flask import Flask, request, jsonify
from web3 import Web3
from web3.middleware import geth_poa_middleware
import sys, time
from hexbytes import HexBytes
import logging
import re
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
nonce_lock = threading.Lock()
MAX_FUND_AMOUNT = {max_fund_amount}

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

def get_balance(web3, account):
    logging.info("--------- Checking Balance ---------")
    # Get the account balance in Wei
    balance_wei = web3.eth.get_balance(account)

    # Convert the balance from Wei to Ether
    balance_eth = web3.fromWei(balance_wei, 'ether')
    logging.info("Account: {{}}, Balance : {{}}".format(account, balance_eth))

    return balance_eth

# Send raw transaction
def send_raw_transaction_no_wait(web3, sender, sender_key, recipient, amount, nonce, data):
    try:
        logging.info("---------Sending Raw Transaction ---------------")
        tx = construct_raw_transaction(sender, recipient, nonce, amount, data)
        signed_tx  = web3.eth.account.signTransaction(tx, sender_key)
        tx_hash    = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        logging.info("Transaction Hash: {{}}".format(tx_hash.hex()))
        return tx_hash
    except ValueError as e:
        raise RuntimeError(f'Error sending transaction: {{e}}')

def wait_for_transaction_receipt(web3, tx_hash):
    try:
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        logging.info("Transaction Receipt: {{}}".format(tx_receipt))
        return tx_receipt
    except ValueError as e:
        raise RuntimeError(f'Error sending transaction: {{e}}')
        

def create_account(web3:Web3):
    # Generate a new Ethereum account
    account = web3.eth.account.create()
    return account


@app.route('/')
def index():
    return 'OK', 200

# Route for handling form submission
@app.route('/fundme', methods=['POST'])
def submit_form():
    if request.is_json:
        # If the request is JSON
        data = request.get_json()
        recipient = data.get('address')
        amount = data.get('amount')
    else:
        recipient = request.form.get('address')
        amount = request.form.get('amount')

    ip_address = request.remote_addr
    logging.info(f"recipient: {{recipient}} amount: {{amount}} sender ip: {{ip_address}}")
    
    # Check if 'recipient' is not None and follows the format of an Ethereum account
    if recipient is None:
        logging.info("address cannot be empty")
        return jsonify({{'status': 'error', 'message': 'address cannot be empty'}}), 500
    elif not re.match(r'^0x[a-fA-F0-9]{{40}}$', recipient):
        logging.info("Invalid Ethereum Address")
        return jsonify({{'status': 'error', 'message': 'Invalid Ethereum address'}}), 500

    if amount is None:
        logging.info("amount cannot be empty")
        return jsonify({{'status': 'error', 'message': 'amount cannot be empty'}}), 500
    # Check if 'amount' is a number and less than 10
    try:
        amount = int(amount)
        if amount < 0:
            logging.info("amount should be a number larger than 0")
            return jsonify({{'status': 'error', 'message': 'Amount should be a number larger than 0'}}), 500
        if amount > MAX_FUND_AMOUNT:
            logging.info("Amount should not be larger than max_fund_amount")
            return jsonify({{'status': 'error', 'message': f'Amount should not be larger max_fund_amount: {{MAX_FUND_AMOUNT}}'}}), 500
        if amount > get_balance(app.config['WEB3'], app.config['SENDER_ADDRESS']):
            logging.info("Request fund amount is larger than the Faucet account balance")
            return jsonify({{'status': 'error', 'message': 'Request fund amount is larger than the Faucet account balance.'}}), 500
    except ValueError:
        logging.info("amount should be a number")
        return jsonify({{'status': 'error', 'message': 'Amount should be a number'}}), 500
    
    # nonce = 1
    with nonce_lock:
        app.config['NONCE'] = max(app.config['NONCE']+1, app.config['WEB3'].eth.getTransactionCount(app.config['SENDER_ADDRESS']))
        nonce = app.config['NONCE']
        try:
            tx_hash = send_raw_transaction_no_wait(app.config['WEB3'], app.config['SENDER_ADDRESS'], app.config['SENDER_KEY'], recipient, amount, nonce, '')
        except Exception as e:
            return jsonify({{'status': 'error', 'message': f'Error sending transaction: {{e}}'}}), 500
    try:
        tx_receipt = wait_for_transaction_receipt(app.config['WEB3'], tx_hash)
        return jsonify({{'status': 'success', 'message':f'Funds successfully sent to {{recipient}} for amount {{amount}}.\\n{{tx_receipt}}'}}) , 200
    except Exception as e:
        return jsonify({{'status': 'error', 'message': f'Error sending transaction: {{e}}'}}), 500

if __name__ == '__main__':
    trial = 20
    while trial > 0:
        trial -= 1
        web3 = connect_to_geth('http://{eth_server_url}:{eth_server_http_port}', '{consensus}')
        if web3 == "":
            time.sleep(10)
        else:
            app.config['WEB3'] = web3
            break
        if trial == 0:
            sys.exit("Connection failed!")

    while web3.eth.blockNumber < 2:
        time.sleep(10)
    
    app.config['SENDER_ADDRESS'] = "{account_address}"
    app.config['SENDER_KEY'] = "{account_key}"
    app.config['NONCE'] = app.config['WEB3'].eth.getTransactionCount(app.config['SENDER_ADDRESS']) - 1
    app.run(host='0.0.0.0', port={port}, debug=True)

'''

class FaucetUtil(Configurable):
    __vnode_name:str
    __port:int
    __fund_list:list
    __faucet_server_address:str
    __is_configured:bool

    def __init__(self):
        super().__init__()
        self.__is_configured = False
        self.__fund_list = []
        self.__vnode_name = ""
        self.__port = -1
        self.__faucet_server_address = ""

    def configure(self, emulator: Emulator):
        super().configure(emulator)
        self.__faucet_server_address = self.__getIpByVnodeName(nodename=self.__vnode_name, emulator=emulator)
        assert self.__faucet_server_address != '', 'Failed to get ip address of the faucet server by its vnode name. please check the vnode name is valid'
        self.__is_configured = True

    def setFaucetServerInfo(self, vnode, port):
        self.__vnode_name = vnode
        self.__port = port
        return self

    def addFund(self, recipientAddress:str, amount:int):
        self.__fund_list.append((recipientAddress, amount))
        return self
    
    def getFaucetFundUrl(self):
        return FaucetServerFileTemplates['faucet_fund_url'].format(address=self.__faucet_server_address,
                                                            port = self.__port)
    
    def getFacuetUrl(self):
        return FaucetServerFileTemplates['faucet_url'].format(address=self.__faucet_server_address,
                                                            port = self.__port)
     
    
    def getFundApi(self, recipientAddress:str, amount:int):
        return FaucetServerFileTemplates['fund_curl'].format(recipient=recipientAddress, 
                                                            amount=amount,
                                                            address=self.__faucet_server_address,
                                                            port = self.__port)
    def getFundScript(self):
        assert self.__is_configured, 'configure method should be called ahead.'
        
        funds_list = []
        for recipient, amount in self.__fund_list:
            funds_list.append(FaucetServerFileTemplates['fund_curl'].format(recipient=recipient, 
                                                                            amount=amount,
                                                                            address=self.__faucet_server_address,
                                                                            port = self.__port))
            
        return FaucetServerFileTemplates['fund_script'].format(address=self.__faucet_server_address, 
                                                               port=self.__port,
                                                               fund_command=';'.join(funds_list))
    
    def __getIpByVnodeName(self, nodename:str, emulator:Emulator) -> str:
        node = emulator.getBindingFor(nodename)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                return address