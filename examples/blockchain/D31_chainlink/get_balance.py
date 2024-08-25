#!/bin/env python3

import os, json, logging
from EthereumHelper import EthereumHelper

###########################################
eth_url    = "http://10.150.0.71:8545"
chain_id   = 1337
###########################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)


with open('./info/user_account.json', 'r') as f:
     user_account = json.load(f)
address_user_account = user_account['account_address']

with open('./info/contract_addresses.json', 'r') as f:
     contract_addresses = json.load(f)
address_link_contract = contract_addresses['link_token_contract_address']
addresses_oracle = contract_addresses['oracle_contracts']

with open('./info/user_contract.json', 'r') as f:
     user_contract = json.load(f)
address_user_contract = user_contract['contract_address']

with open('./contracts/link_token.abi', 'r') as f:
     link_token_abi = f.read()

link_contract = web3.eth.contract(address=address_link_contract, 
                                  abi=link_token_abi)

# Check the balance of user contract
balance = link_contract.functions.balanceOf(address_user_contract).call()
logging.info("---------------------------------- " + str(1000000000000000000))
logging.info("User account  ETH  balance:       " + 
             str(web3.eth.get_balance(address_user_account)))
logging.info("User contract LINK balance:       " + str(balance))
logging.info("LINK contract ETH  balance:       " + 
             str(web3.eth.get_balance(address_link_contract)))
logging.info("User contract ETH  balance:       " + 
             str(web3.eth.get_balance(address_user_contract)))
i = 0
for oracle in addresses_oracle:
    b = link_contract.functions.balanceOf(oracle).call()
    logging.info("Oracle contract {}'s LINK balance: {}".format(i,b))
    i = i + 1


