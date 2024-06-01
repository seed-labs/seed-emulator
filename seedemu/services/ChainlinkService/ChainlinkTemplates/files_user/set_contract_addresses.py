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

# Load the oracle contracts and link token contract address
with open('./info/contract_addresses.json', 'r') as f:
    contract_addresses = json.load(f)
    
oracle_contracts = contract_addresses.get('oracle_contracts', [])
link_token_contract_address = contract_addresses.get('link_token_contract_address', '')

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
set_link_token_function = user_contract.functions.setLinkToken(link_token_contract_address)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
set_link_token_tx = set_link_token_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(set_link_token_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
    logging.error("Failed to set Link Token contract address in user contract.")
    exit()
logging.info("Set Link Token contract address in user contract mined successfully.")

# Set the oracle contracts in the user contract
job_id = "7599d3c8f31e4ce78ad2b790cbcfc673"
add_oracle_function = user_contract.functions.addOracles(oracle_contracts, job_id)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
add_oracle_tx = add_oracle_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(add_oracle_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
# If the status is 0, the transaction failed
if tx_receipt['status'] == 0:
    logging.error("Failed to set oracle contracts in user contract.")
    exit()
logging.info("Add oracles function in user contract mined successfully.")
