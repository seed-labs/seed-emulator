#!/bin/env python3

import time
import json, os, logging
from EthereumHelper import EthereumHelper


###########################################
eth_url      = "http://{eth_server}:{eth_server_http_port}"
faucet_url   = "http://{faucet_server}:{faucet_server_port}"
chain_id     = {chain_id}
external_url = "{external_url}"
path         = "{path}"
###########################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Load user account information
with open('./info/user_account.json', 'r') as f:
	user_account = json.load(f)
user_address = user_account['account_address']
user_key     = user_account['private_key']


# Load the user contract address
with open('./info/user_contract.json', 'r') as f:
    user_contract = json.load(f)
user_contract_address = user_contract['contract_address']

# Load the user contract ABI
with open('./contracts/user_contract.abi', 'r') as f:
    user_contract_abi = f.read()

# Invoke the user contract
user_contract = web3.eth.contract(address=user_contract_address, abi=user_contract_abi)
request_eth_price_function = user_contract.functions.requestETHPriceData(
                                        external_url, path) 
_, tx_receipt = eth.invoke_contract_function(request_eth_price_function, 
                            user_address, user_key)
if tx_receipt['status'] == 0:
     logging.error("Failed to request ETH price data.")
     exit()
logging.info("Requested ETH price data successfully.")

# Wait for responses to be received
response_count = 0
while response_count < 1:
     response_count = user_contract.functions.responsesCount().call()
     logging.info(f"Awaiting responses... Current responses count: " + str(response_count))
     time.sleep(10)

average_price = user_contract.functions.averagePrice().call()
logging.info("Response count: " + str(response_count))
logging.info("Average ETH price: " + str(average_price))
logging.info("Chainlink user example service completed.")

