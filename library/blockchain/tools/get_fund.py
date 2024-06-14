#!/bin/env python3

import sys
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper

###############################################################
# Import global variables related to the emulator
from emulator_setup import chain_id, eth_url, faucet_url
###############################################################

if len(sys.argv) < 2:
    print("Usage: get_fund <address>")
    exit()

address = sys.argv[1]

# Fund the account
faucet = FaucetHelper(faucet_url)
faucet.wait_for_server_ready()

print("Send fundme request to faucet ...")
faucet.send_fundme_request(address, 10)
print("Account funded")


eth = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

amount = web3.eth.get_balance(address)
print(web3.fromWei(amount, 'ether'))

