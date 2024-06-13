#!/bin/env python3

import os, json, logging, socket
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper
from lib.UtilityServerHelper import UtilityServerHelper

##############################################
# Import global variables related to the emulator
from emulator_setup import *

CONTRACT = '../contract/SEEDToken20'
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

address = SEED_ADDRESS
key     = SEED_KEY

# Deploy the oracle contract
#_, receipt = eth.deploy_contract(CONTRACT + '.bin', address, key)

with open(CONTRACT + '.abi', 'r') as f:
      contract_abi = f.read()
with open(CONTRACT + '.bin', 'r') as f:
      contract_bin = f.read().strip()

contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bin)

cfunc = contract.constructor('SEED', 'STK', 2)
_, receipt = eth.invoke_contract_function(cfunc, address, key)

logging.info(f"Deployed contract address: " + str(receipt.contractAddress))

data = dict() 
data['account_address'] = address
data['private_key']     = key
data['contract_address']  = receipt.contractAddress
with open('./info.json', 'w') as f:
    json.dump(data, f)    # save user account information to a file
