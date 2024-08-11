#!/bin/env python3

import os, json, logging
from EthereumHelper import EthereumHelper

###########################################
eth_url    = "http://{eth_server}:{eth_server_http_port}"
chain_id   = {chain_id}
###########################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Load user account information
with open('./info/user_account.json', 'r') as f:
     user_account = json.load(f)
user_address = user_account['account_address']
user_key     = user_account['private_key']



# Load the link token contract address
with open('./info/contract_addresses.json', 'r') as f:
     contract_addresses = json.load(f)
link_contract_address = contract_addresses['link_token_contract_address']
#link_contract_address = web3.toChecksumAddress(link_contract_address)


# Send 1 Ether to the link contract 
_, tx_receipt = eth.transfer_fund(link_contract_address, 
                                  user_address, user_key,
                                  amount=1)
if tx_receipt['status'] == 0:
     logging.error("Failed to send 1 ETH to LINK token contract.")
     exit()
logging.info("Sent 1 ETH to LINK token contract successfully.")



# Transfer 100 LINK tokens to the user contract (invoke Link contract)
with open('./info/user_contract.json', 'r') as f:
     user_contract = json.load(f)
with open('./contracts/link_token.abi', 'r') as f:
     link_token_abi = f.read()

user_contract_address = user_contract['contract_address']

link_amount_to_transfer = web3.toWei(100, 'ether')

link_contract = web3.eth.contract(address=link_contract_address, abi=link_token_abi)
link_transfer_function = link_contract.functions.transfer(
                               user_contract_address, 
                               link_amount_to_transfer)
tx_hash, tx_receipt = eth.invoke_contract_function(link_transfer_function,
                                                   user_address, user_key)
if tx_receipt['status'] == 0:
     logging.error("Failed to transfer LINK tokens to user contract.")
     exit()
logging.info("Transferred LINK tokens to user contract successfully.")

# Check the balance of user contract
balance = link_contract.functions.balanceOf(user_contract_address).call()
logging.info("User contract balance: " + str(balance))

