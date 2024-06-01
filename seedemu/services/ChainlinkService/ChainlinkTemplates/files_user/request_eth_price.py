#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
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

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Load user account information
with open('./info/user_account.json', 'r') as f:
	user_account = json.load(f)

account_address = user_account.get('account_address', '')
private_key = user_account.get('private_key', '')


# Load the user contract address
with open('./info/user_contract.json', 'r') as f:
    user_contract = json.load(f)

user_contract_address = user_contract.get('contract_address', '')

# Load the user contract ABI
with open('./contracts/user_contract.abi', 'r') as f:
    user_contract_abi = f.read()

user_contract = web3.eth.contract(address=user_contract_address, abi=user_contract_abi)
request_eth_price_data_function = user_contract.functions.requestETHPriceData("{url}", "{path}")
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
invoke_request_eth_price_data_tx = request_eth_price_data_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(invoke_request_eth_price_data_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
	logging.error("Failed to request ETH price data.")
	exit()
logging.info("Requested ETH price data successfully.")

# Wait for responses to be received
response_count = 0
while response_count < {number_of_normal_servers}:
	response_count = user_contract.functions.responsesCount().call()
	logging.info(f"Awaiting responses... Current responses count: {{response_count}}")
	time.sleep(10)

average_price = user_contract.functions.averagePrice().call()
logging.info(f"Response count: {{response_count}}")
logging.info(f"Average ETH price: {{average_price}}")
logging.info("Chainlink user example service completed.")
