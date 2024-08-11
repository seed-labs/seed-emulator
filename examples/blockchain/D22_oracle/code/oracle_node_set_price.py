#!/bin/env python3

import os, json, logging, time, random, socket
from web3 import Web3
from FaucetHelper import FaucetHelper
from EthereumHelper import EthereumHelper


##############################################
chain_id    = {chain_id}
faucet_url  = "http://{faucet_server}:{faucet_port}"
utility_url = "http://{utility_server}:{utility_port}"

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

eth = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Get data 
with open('./oracle_account.json', 'r') as f:
    data = json.load(f)   
account_address = data['account_address']
account_key     = data['private_key']   
oracle_address  = data['oracle_address'] 

# Invoke the oracle contract to set price  
with open('../contract/Oracle.abi', 'r') as f:
     oracle_abi = f.read()

oracle_contract = web3.eth.contract(address=oracle_address, abi=oracle_abi)

previous_blocknumber = 0
while True:
   # Monitor event 
   logs = oracle_contract.events.UpdatePriceMessage().getLogs(fromBlock="latest")
   if not logs:
       print("Sleeping for 10 seconds ...")
       time.sleep(10)
       continue

   for log in logs:
      blocknumber = log['blockNumber']
      if blocknumber <= previous_blocknumber: 
          pass
      else: 
          previous_blocknumber = blocknumber

   # Invoke the setPrice() 
   price = random.randint(0, 99) 
   setPriceFunc = oracle_contract.functions.setPrice(price)
   _, receipt = eth.invoke_contract_function(setPriceFunc, account_address, account_key)
   
   if receipt['status'] == 0:
       logging.error("Failed to set price in the oracle contract.")
   else:
       logging.info("Successfully set price in the oracle contract.") 


