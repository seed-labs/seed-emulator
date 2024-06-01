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

link_token_abi = None
with open('./contracts/link_token.abi', 'r') as f:
	link_token_abi = f.read()

# Load the link token contract address
with open('./info/contract_addresses.json', 'r') as f:
	contract_addresses = json.load(f)

link_token_contract_address = contract_addresses.get('link_token_contract_address', '')
link_token_contract_address = web3.toChecksumAddress(link_token_contract_address)

link_token_contract = web3.eth.contract(address=link_token_contract_address, abi=link_token_abi)

transaction_info = {{
    'from': account_address,
    'to': link_token_contract_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'gasPrice': web3.toWei(50, 'gwei'),
    'value': web3.toWei(1, 'ether'),
    'chainId': {chain_id}
}}
signed_tx = web3.eth.account.sign_transaction(transaction_info, private_key)
eth_to_link_tx = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
eth_to_link_tx_receipt = web3.eth.wait_for_transaction_receipt(eth_to_link_tx, timeout=300)
if eth_to_link_tx_receipt['status'] == 0:
	logging.error("Failed to send 1 ETH to LINK token contract.")
	exit()
logging.info("Sent 1 ETH to LINK token contract successfully.")

# Transfer 100 LINK tokens to the user contract
with open('./info/user_contract.json', 'r') as f:
	user_contract = json.load(f)

user_contract_address = user_contract.get('contract_address', '')
user_contract_address = web3.toChecksumAddress(user_contract_address)

link_amount_to_transfer = web3.toWei(100, 'ether')
transfer_function = link_token_contract.functions.transfer(user_contract_address, link_amount_to_transfer)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
transfer_tx = transfer_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(transfer_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
	logging.error("Failed to transfer LINK tokens to user contract.")
	exit()
logging.info("Transferred LINK tokens to user contract successfully.")

# Check the balance of user contract
balance = link_token_contract.functions.balanceOf(user_contract_address).call()
logging.info(f"User contract balance: {{balance}}")
