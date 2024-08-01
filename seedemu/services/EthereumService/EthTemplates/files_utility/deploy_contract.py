#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import os
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RPC_URL    = "http://{rpc_url}:{rpc_port}"
CHAIN_ID   = {chain_id}
DIR_PREFIX = "{dir_prefix}"

with open(DIR_PREFIX + '/contracts/contract_file_paths.txt') as contract_path_file:
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
    file_path = DIR_PREFIX + '/account.json'

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

    directory = DIR_PREFIX + '/deployed_contracts'

    if not os.path.exists(directory):
        os.makedirs(directory)
        with open(DIR_PREFIX + '/deployed_contracts/contract_address.txt', 'w') as address_file:
            contract_address = {{
                contract_name: tx_receipt.contractAddress
            }}
            json.dump(contract_address, address_file, indent=4)
    else:
        with open(DIR_PREFIX + '/deployed_contracts/contract_address.txt', 'r') as address_file:
            contract_address = json.load(address_file)
        contract[contract_name] = tx_receipt.contractAddress
        with open(DIR_PREFIX + '/deployed_contracts/contract_address.txt', 'w') as address_file:
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
