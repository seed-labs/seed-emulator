#!/bin/env python3

import sys
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper

###############################################################
# Import global variables related to the emulator
from emulator_setup import emu_sender_address, emu_sender_key, chain_id, eth_url
###############################################################

if len(sys.argv) < 3: 
    print("Usage: send_fund <address> <amount>")
    exit()

receiver_address = sys.argv[1]
amount = sys.argv[2]

eth = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

tx_hash, tx_receipt = eth.transfer_fund(receiver_address, 
                         emu_sender_address, emu_sender_key, amount)
print(tx_receipt)

amount = web3.eth.get_balance(receiver_address)
print(web3.fromWei(amount, 'ether'))
