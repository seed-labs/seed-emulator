#!/bin/env python3
import time
import logging
import os
from queue import Queue
from web3 import Web3, HTTPProvider
import re
import requests
import json

rpc_url = "http://{rpc_ip}:{rpc_port}"
faucet_ip = "http://{faucet_ip}:{faucet_port}"

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s')

contract_folder = './contracts/'

# If the deployment of the oracle contract fails, 
# the script will retry after this number of seconds
retry_delay = 20

deployment_queue = Queue()
deployment_queue.put({{}})

url = "http://{util_node_ip}:{util_node_port}/contracts_info?name={contract_name}"
response = requests.get(url)
link_address = response.text.strip().replace('"', '')

logging.info("Link contract address: " + link_address)

if link_address:
	link_address = Web3.toChecksumAddress(link_address)
else:
	logging.error("Failed to get Link Token contract address.")

web3 = Web3(HTTPProvider(rpc_url))
if not web3.isConnected():
    logging.error("Failed to connect to Ethereum node.")
    exit()

new_account = web3.eth.account.create()
owner_address = new_account.address
private_key = new_account.privateKey.hex()

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get(faucet_ip)
        if response.status_code == 200:
            logging.info("faucet server connection succeed.")
            break
        logging.info("faucet server connection failed: try again 10 seconds after.")
        
        time.sleep(10)
        if time.time() - start_time > timeout:
            logging.info("faucet server connection failed: 600 seconds exhausted.")
            exit()
    except Exception as e:
        pass


def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_ip = "http://{faucet_ip}:{faucet_port}/fundme"
	try:
		response = requests.post(request_ip, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
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
			send_fundme_request(owner_address)
	except Exception as e:
		logging.error(f"An error occurred: {{str(e)}}")
		exit()

# Send /fundme request to faucet server
send_fundme_request(owner_address)

isAccountFunded = False
start = time.time()
timeout = 100
while time.time() - start < timeout:
	balance = web3.eth.get_balance(owner_address)
	if balance > 0:
		isAccountFunded = True
		break
	time.sleep(5)
 

if isAccountFunded:
	logging.info(f"Account funded: {{owner_address}}")
else:
	logging.error(f"Failed to fund account: {{owner_address}}")
	exit()

with open(os.path.join(contract_folder, 'oracle_contract.abi'), 'r') as abi_file:
    contract_abi = abi_file.read()
with open(os.path.join(contract_folder, 'oracle_contract.bin'), 'r') as bin_file:
    contract_bytecode = bin_file.read().strip()
account = web3.eth.account.from_key(private_key)

gas_price = web3.eth.gasPrice
while not deployment_queue.empty():
    try:
        deployment_queue.get()
        nonce = web3.eth.getTransactionCount(account.address, 'pending')
        OracleContract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        transaction = OracleContract.constructor(link_address, owner_address).buildTransaction({{
            'from': account.address,
            'nonce': nonce,
            'gas': 4000000,
            'gasPrice': gas_price
        }})
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logging.info(f"Attempting to deploy contract, TX Hash: {{tx_hash.hex()}}")

        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if tx_receipt.status == 1:
            logging.info(f"Oracle Contract deployed at: {{tx_receipt.contractAddress}}")
            directory = './deployed_contracts'
            if not os.path.exists(directory): os.makedirs(directory)
            with open('./deployed_contracts/oracle_contract_address.txt', 'w') as address_file:
                address_file.write(f"{{tx_receipt.contractAddress}}")
            contract_address = tx_receipt.contractAddress
        else:
            logging.error("Transaction failed. Retrying...")
            deployment_queue.put({{}})
            time.sleep(retry_delay)

    except Exception as e:
        logging.error(f"An error occurred during contract deployment: {{e}}. Retrying...")
        deployment_queue.put({{}})
        time.sleep(retry_delay)
        
def authorize_address(sender, oracle_contract_address, nonce):
    try:
        oracle_contract = web3.eth.contract(address=oracle_contract_address, abi=contract_abi)
        txn_dict = oracle_contract.functions.setAuthorizedSenders([sender]).buildTransaction({{
            'chainId': {chain_id},
            'gas': 4000000,
            'gasPrice': web3.toWei('50', 'gwei'),
            'nonce': nonce,
        }})
        signed_txn = web3.eth.account.sign_transaction(txn_dict, account.privateKey)
        txn_receipt = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(txn_receipt)
        logging.info(f'Success: {{txn_receipt}}')
        logging.info(f'Successfully set authorized sender: {{sender}} in Oracle contract: {{oracle_contract_address}}')
        return True
    except Exception as e:
        logging.error(f'Error: {{e}}')
        if "replacement transaction underpriced" in str(e):
            logging.warning('Requeuing due to underpriced transaction')
            return False
        else:
            return True

with open('./deployed_contracts/auth_sender.txt', 'r') as file:
    sender = file.read().strip()
authorization_success = False
while not authorization_success:
    nonce = web3.eth.getTransactionCount(owner_address, 'pending')
    authorization_success = authorize_address(sender, contract_address, nonce)
    if not authorization_success:
        time.sleep(retry_delay)

