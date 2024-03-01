#!/bin/env python3

from web3 import Web3
import requests
import json

web3 = Web3(Web3.HTTPProvider("http://10.164.0.71:8545")) # Connect to the Ethereum node via RPC

private_key = "<Private Key>" # Private key of the account that will use the LinkToken for transactions

with open('./link_token.abi', 'r') as abi_file:
    contract_abi = abi_file.read()
with open('./link_token.bin', 'r') as bin_file:
    contract_bytecode = bin_file.read()

# Create the contract in Web3
MyContract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

# Account info for deploying the contract
account = web3.eth.account.from_key(private_key)
nonce = web3.eth.get_transaction_count(account.address)

# Prepare the deployment transaction
transaction = MyContract.constructor().buildTransaction({
    'from': account.address,
    'nonce': nonce,
    'gas': 2000000,
    'gasPrice': web3.eth.gas_price
})

# Sign the transaction
signed_txn = web3.eth.account.sign_transaction(transaction, private_key)

# Send the transaction
tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

# Wait for the transaction to be mined
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

# The contract is now deployed on the blockchain!
print(f"Contract deployed at address: {tx_receipt.contractAddress}")
