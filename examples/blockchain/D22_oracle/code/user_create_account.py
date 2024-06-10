#!/bin/env python3

import os, json, logging, socket
from FaucetHelper import FaucetHelper
from EthereumHelper import EthereumHelper

##############################################
chain_id    = {chain_id}
faucet_url  = "http://{faucet_server}:{faucet_port}"

# Ethereum nodes can only be accessed using IP address, not hostname
ip      = socket.gethostbyname("{eth_node}")
eth_url = "http://" + ip + ":{eth_port}"
##############################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to blockchain
eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Create a new account 
account_address, account_key = eth.create_account()

# Fund the account 
faucet = FaucetHelper(faucet_url)
faucet.wait_for_server_ready()
faucet.send_fundme_request(account_address, 10)
logging.info("Account funded")

data = dict() 
data['account_address'] = account_address
data['private_key']     = account_key
with open('./user_account.json', 'w') as f:
    json.dump(data, f)    # save user account information to a file

