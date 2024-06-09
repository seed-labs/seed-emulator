#!/bin/env python3

import os, json, logging, time, socket
from FaucetHelper import FaucetHelper
from EthereumHelper import EthereumHelper
from UtilityServerHelper import UtilityServerHelper

##############################################
chain_id    = {chain_id}
faucet_url  = "http://{faucet_server}:{faucet_port}"
utility_url = "http://{utility_server}:{utility_port}"

# Ethereum nodes can only be accessed using IP address, not hostname 
ip      = socket.gethostbyname("{eth_node}")
eth_url = "http://" + ip + ":{eth_port}"

oracle_contract_name = "{oracle_contract_name}"  
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

# Get oracle contract address
util_server = UtilityServerHelper(utility_url)
util_server.wait_for_server_ready()
oracle_address = util_server.get_contract_address(oracle_contract_name)

# Load the account data 
with open('./user_account.json', 'r') as f:
    data = json.load(f)   
address = data['account_address']
key     = data['private_key']


with open('../contract/Oracle.abi', 'r') as f:
    oracle_abi = f.read()
oracle_contract = web3.eth.contract(address=oracle_address, abi=oracle_abi)

# Invoke the updatePrice() 
updateFunc = oracle_contract.functions.updatePrice()
_, receipt = eth.invoke_contract_function(updateFunc, address, key)

if receipt['status'] == 0:
    logging.error("Failed to invoke updatePrice().")
else:
    logging.info("Successfully invoke updatePrice().")


# Keep polling the blockchain for the updated price 
while True:
   price = oracle_contract.functions.getPrice().call()
   print("Price " + str(price))
   time.sleep(10)

