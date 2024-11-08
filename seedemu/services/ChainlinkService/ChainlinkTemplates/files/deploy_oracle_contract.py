#!/bin/env python3

import os, logging, time, json
from FaucetHelper import FaucetHelper
from UtilityServerHelper import UtilityServerHelper
from EthereumHelper import EthereumHelper


###############################################################
chain_id   = {chain_id}
eth_url    = "http://{eth_server}:{eth_server_http_port}"
faucet_url = "http://{faucet_server}:{faucet_server_port}"
util_server_url    = "http://{util_server}:{util_server_port}"
link_contract_name = "{link_contract_name}"
###############################################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname   = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s')

# Get Link contract address 
util_server  = UtilityServerHelper(util_server_url)
link_address = util_server.get_contract_address(link_contract_name)

# Create account
eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)
owner_address, owner_key = eth.create_account()

# Fund the account
faucet = FaucetHelper(faucet_url)
faucet.wait_for_server_ready()
faucet.send_fundme_request(owner_address, 10)

with open('./contracts/oracle_contract.abi', 'r') as abi_file:
     contract_abi = abi_file.read()
with open('./contracts/oracle_contract.bin', 'r') as bin_file:
     contract_bytecode = bin_file.read().strip()

# Deploy the oracle contract
try:
    oracle_contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    transaction = oracle_contract.constructor(link_address, owner_address).\
       buildTransaction({{
            'from': owner_address,
            'nonce': web3.eth.getTransactionCount(owner_address, 'pending'),
            'gas': 4000000,
            'gasPrice': web3.eth.gasPrice
       }})

    signed_txn = web3.eth.account.sign_transaction(transaction, owner_key)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
    if tx_receipt.status == 1:
        logging.info(f"Oracle contract deployed at: " + tx_receipt.contractAddress)

        # Save the oracle contract address to a file 
        directory = './info'
        if not os.path.exists(directory): os.makedirs(directory)
        with open('./info/oracle_contract_address.txt', 'w') as address_file:
                address_file.write(tx_receipt.contractAddress)

        oracle_contract_address = tx_receipt.contractAddress
    else:
        logging.error("Transaction failed")
        exit()

except Exception as e:
        logging.error(f"An error occurred during contract deployment: {{e}}")
        exit()

        
# Set the auth-sender as the authorized sender
with open('./info/auth_sender.txt', 'r') as file:
    sender = file.read().strip()

oracle_contract = web3.eth.contract(address=oracle_contract_address, abi=contract_abi)
set_auth_function = oracle_contract.functions.setAuthorizedSenders([sender])
tx_hash, tx_receipt = eth.invoke_contract_function(set_auth_function,
                             owner_address, owner_key, gas=4000000)
if tx_receipt['status'] == 0:
     logging.error("Failed to authorize user.")
     exit()
logging.info("Authorizing user successfully.")


