#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)
    
logging.info("Successfully connected to the Ethereum node.")

new_account = web3.eth.account.create()
account_address = new_account.address
private_key = new_account.privateKey.hex()

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get(faucet_url)
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

# Send /fundme request to faucet server
send_fundme_request(account_address)
timeout = 100
isAccountFunded = False
start = time.time()
while time.time() - start < timeout:
	balance = web3.eth.get_balance(account_address)
	if balance > 0:
		isAccountFunded = True
		break
	time.sleep(5)
 

if isAccountFunded:
	logging.info(f"Account funded: {{account_address}}")
else:
	logging.error(f"Failed to fund account: {{account_address}}")
	exit()

with open('./contracts/link_token.abi', 'r') as abi_file:
	contract_abi = abi_file.read()
with open('./contracts/link_token.bin', 'r') as bin_file:
	contract_bytecode = bin_file.read().strip()

link_token_contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

account = web3.eth.account.from_key(private_key)
nonce = web3.eth.get_transaction_count(account.address)

transaction = link_token_contract.constructor().buildTransaction({{
	'from': account.address,
	'nonce': nonce,
	'gas': 2000000,
	'gasPrice': web3.eth.gas_price,
	'chainId': {chain_id}
}})

signed_txn = web3.eth.account.sign_transaction(transaction, private_key)

tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

print(f"Link Token Contract deployed at address: {{tx_receipt.contractAddress}}")

directory = './deployed_contracts'

if not os.path.exists(directory):
    os.makedirs(directory)

with open('./deployed_contracts/link_token_address.txt', 'w') as address_file:
	address_file.write(tx_receipt.contractAddress)

with open('./deployed_contracts/sender_account.txt', 'w') as account_file:
	account_file.write(f"Address: {{account_address}}\\nPrivate Key: {{private_key}}")
