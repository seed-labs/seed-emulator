#!/bin/env python3

import json, os, logging
from EthereumHelper import EthereumHelper 

#############################################
eth_url    = "http://{eth_server}:{eth_server_http_port}"
faucet_url = "http://{faucet_server}:{faucet_server_port}"
chain_id   = {chain_id} 
#############################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Load the oracle contracts and link token contract address
with open('./info/contract_addresses.json', 'r') as f:
    contract_addresses = json.load(f)
    
oracle_contracts = contract_addresses.get('oracle_contracts', [])
link_token_contract_address = contract_addresses.get('link_token_contract_address', '')

# Load the user account and contract information
with open('./info/user_account.json', 'r') as f:
    user_account = json.load(f)
with open('./info/user_contract.json', 'r') as f:
    user_contract = json.load(f)
with open('./contracts/user_contract.abi', 'r') as f:
    user_contract_abi = f.read()
    
user_account_address  = user_account.get('account_address', '')
user_key              = user_account.get('private_key', '')
user_contract_address = user_contract.get('contract_address', '')

user_contract = web3.eth.contract(address=user_contract_address, 
                                  abi=user_contract_abi)

# Invoke the user contract to set the link token address
set_link_token_function = user_contract.functions.setLinkToken(link_token_contract_address)
tx_hash, tx_receipt     = eth.invoke_contract_function(set_link_token_function, 
                                                       user_account_address, user_key)
if tx_receipt['status'] == 0:
    logging.error("Failed to set Link token contract address in user contract.")
    exit()
logging.info("Successfully set Link token contract address in user contract.")


# Invoke the user contract to add oracles 
job_id = "7599d3c8f31e4ce78ad2b790cbcfc673"
add_oracle_function = user_contract.functions.addOracles(oracle_contracts, job_id)
tx_hash, tx_receipt = eth.invoke_contract_function(add_oracle_function, 
                                                   user_account_address, user_key)
if tx_receipt['status'] == 0:
    logging.error("Failed to add oracles to user contract.")
    exit()
logging.info("Successfully add oracles to user contract.")

