#!/bin/env python3

import os, json, logging
from FaucetHelper import FaucetHelper
from UtilityServerHelper import UtilityServerHelper
from EthereumHelper import EthereumHelper

##############################################
eth_url    = "http://{eth_server}:{eth_server_http_port}"
faucet_url = "http://{faucet_server}:{faucet_server_port}"
chain_id   = {chain_id}
##############################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Create the user account 
eth = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)
user_address, user_key = eth.create_account()
logging.info("User account address: " + user_address)
data = dict()
data['account_address'] = user_address
data['private_key']     = user_key
with open('./info/user_account.json', 'w') as f:
    json.dump(data, f)    # save user account information to a file

# Fund the user account 
faucet = FaucetHelper(faucet_url)
faucet.wait_for_server_ready()
faucet.send_fundme_request(user_address, 10)

# Deploy the user contract
_, receipt = eth.deploy_contract('./contracts/user_contract.bin', 
                                 user_address, user_key)
logging.info(f"User contract address: " + str(receipt.contractAddress))
data = dict()
data['contract_address'] = receipt.contractAddress

# Save the contract address to a file
directory = './info'
if not os.path.exists(directory):
    os.makedirs(directory)
with open(directory + '/user_contract.json', 'w') as f:
    json.dump(data, f)  
