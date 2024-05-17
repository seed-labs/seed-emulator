
from typing import Dict

EthInitializerTemplate: Dict[str, str] = {}

EthInitializerTemplate['fund_account']= '''
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import requests
import logging
import json
from eth_account import Account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RPC_URL = "http://{rpc_url}:{rpc_port}"
FAUCET_URL = "http://{faucet_url}:{faucet_port}"

def connectEthNode():
    web3 = Web3(HTTPProvider(RPC_URL))
    while not web3.isConnected():
        logging.error("Failed to connect to Ethereum node. Retrying...")
        time.sleep(5)
        
    logging.info("Successfully connected to the Ethereum node.")
    return web3

def createAccount():
	new_account = Account.create()
	account_address = new_account.address
	private_key = new_account.privateKey.hex()
	saveAccountAsJson(new_account)
	return account_address, private_key

def saveAccountAsJson(account):
    # Data to be written to the JSON file
    acct = {{
        "address": account.address,
        "private_key": account.privateKey.hex()
    }}

    # File path where the JSON file will be saved
    file_path = '/account.json'

    # Write data to the JSON file
    with open(file_path, 'w') as file:
        json.dump(acct, file, indent=4)
	

# Check if the faucet server is running for 600 seconds
def isFaucetServerUp():
    timeout = 600
    start_time = time.time()
    while True:
        try:
            response = requests.get(FAUCET_URL)
            if response.status_code == 200:
                logging.info("faucet server connection succeed.")
                return True
            logging.info("faucet server connection failed: try again 10 seconds after.")
            
            time.sleep(10)
            if time.time() - start_time > timeout:
                logging.info("faucet server connection failed: 600 seconds exhausted.")
                return False
        except Exception as e:
            pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_url = "http://{faucet_url}:{faucet_port}/fundme"
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

def check_fund_result(web3, account_address):
    timeout = 100
    is_account_funded = False
    start = time.time()
    while time.time() - start < timeout:
        balance = web3.eth.get_balance(account_address)
        if balance > 0:
            is_account_funded = True
            break
        time.sleep(5)
    return is_account_funded

    

if __name__ == "__main__":
    web3 = connectEthNode()
    account_address, private_key = createAccount()

    if not isFaucetServerUp():
        exit()
    
    # Send /fundme request to faucet server
    send_fundme_request(account_address)
    is_account_funded = check_fund_result(web3, account_address)

    if is_account_funded:
        logging.info(f"Account funded: {{account_address}}")
    else:
        logging.error(f"Failed to fund account: {{account_address}}")
        exit()
'''


EthInitializerTemplate['contract_deploy'] = '''
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import os
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RPC_URL = "http://{rpc_url}:{rpc_port}"
CHAIN_ID = {chain_id}
with open('/contracts/contract_file_paths.txt') as contract_path_file:
    CONTRACT_FILE_PATHS = json.load(contract_path_file)

def connectEthNode():
    web3 = Web3(HTTPProvider(RPC_URL))
    while not web3.isConnected():
        logging.error("Failed to connect to Ethereum node. Retrying...")
        time.sleep(5)
        
    logging.info("Successfully connected to the Ethereum node.")
    return web3

def readAccountFromJson():
    # File path of the JSON file to be read
    file_path = '/account.json'

    # Read data from the JSON file
    with open(file_path, 'r') as file:
        acct = json.load(file)

    return acct['address'], acct['private_key']

def deployContract(web3, private_key, contract_name, contract_abi, contract_bytecode):
    contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

    account = web3.eth.account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)

    transaction = contract.constructor().buildTransaction({{
        'from': account.address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': web3.eth.gas_price,
        'chainId': CHAIN_ID
    }})

    signed_txn = web3.eth.account.sign_transaction(transaction, private_key)

    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Contract deployed at address: {{tx_receipt.contractAddress}}")

    directory = '/deployed_contracts'

    if not os.path.exists(directory):
        os.makedirs(directory)
        with open('/deployed_contracts/contract_address.txt', 'w') as address_file:
            contract_address = {{
                contract_name: tx_receipt.contractAddress
            }}
            json.dump(contract_address, address_file, indent=4)
    else:
        with open('/deployed_contracts/contract_address.txt', 'r') as address_file:
            contract_address = json.load(address_file)
        contract[contract_name] = tx_receipt.contractAddress
        with open('/deployed_contracts/contract_address.txt', 'w') as address_file:
            json.dump(contract_address, address_file, indent=4)

if __name__ == "__main__":
    web3 = connectEthNode()
    account_address, private_key = readAccountFromJson()

    for contract_name, paths in CONTRACT_FILE_PATHS.items():
        with open(paths['abi_path'], 'r') as abi_file:
            contract_abi = abi_file.read()
        with open(paths['bin_path'], 'r') as bin_file:
            contract_bytecode = bin_file.read().strip()
        deployContract(web3=web3, private_key=private_key, contract_name=contract_name,
                       contract_abi=contract_abi, contract_bytecode=contract_bytecode)
'''

EthInitializerTemplate['info_server'] = '''\
#!/bin/env python3

from flask import Flask, request, jsonify
import os
from web3 import Web3, HTTPProvider
import json


app = Flask(__name__)

PORT = {port}
ADDRESS_FILE_DIRECTORY = '/deployed_contracts'
ADDRESS_FILE_PATH = '/deployed_contracts/contract_address.txt'
HTML_FILE_PATH = '/var/www/html/index.html'

@app.route('/')
def index():
    return 'OK', 200
    
@app.route('/register_contract', methods=['POST'])
def register_contract():
    name = request.json.get('contract_name')
    address = request.json.get('contract_address')
    if not name:
        return jsonify({{'error': 'No contract name provided'}}), 400
    if not address:
        return jsonify({{'error': 'No contract address provided'}}), 400

    if not os.path.exists(ADDRESS_FILE_DIRECTORY):
        os.makedirs(ADDRESS_FILE_DIRECTORY)
        with open(ADDRESS_FILE_PATH, 'w') as address_file:
            contract_info = {{
                name: address
            }}
            json.dump(contract_info, address_file, indent=4)
        return jsonify(contract_info), 200
        
    else:
        with open(ADDRESS_FILE_PATH, 'r') as address_file:
            contract_info = json.load(address_file)
        contract_info[name] = address
        with open(ADDRESS_FILE_PATH, 'w') as address_file:
            json.dump(contract_info, address_file, indent=4)
        return jsonify(contract_info), 200
        
    
@app.route('/contracts_info', methods=['GET'])
def get_contract_info():
    contract_name = request.args.get('name')

    if not os.path.exists(ADDRESS_FILE_DIRECTORY):
        return jsonify({{}}), 200
    else:
        with open(ADDRESS_FILE_PATH, 'r') as address_file:
            contract_info = json.load(address_file)
        if not contract_name:
            return jsonify(contract_info), 200
        else:
            if contract_name in contract_info.keys():
                return jsonify(contract_info[contract_name]), 200
            else:
                return jsonify({{'error': 'No contract address matching with a given contract name'}}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT)
'''
