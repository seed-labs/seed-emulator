#!/bin/env python3

import os, json, logging, sys
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper
from lib.UtilityServerHelper import UtilityServerHelper
from lib.ContractABIHelper import ContractABIHelper

##############################################
# Import global variables related to the emulator
from emulator_setup import *

CONTRACT_ABI = emu_contract_prefix + '.abi'
CONTRACT_BIN = emu_contract_prefix + '.bin'
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

argv      = sys.argv[1:]
print(argv)

with open(CONTRACT_ABI, 'r') as f:
      abi_content = f.read()
with open(CONTRACT_BIN, 'r') as f:
      bin_content = f.read().strip()

# Get the function information from the abi content (json)
abi_helper = ContractABIHelper(CONTRACT_ABI)

arg_list = abi_helper.construct_arg_list(func_name=None, argv=argv)
print(arg_list)
if arg_list is None:   # No constructor
    _, receipt = eth.deploy_contract(CONTRACT_BIN,
                             emu_sender_address, emu_sender_key)
else:  # Has constructor
    contract = web3.eth.contract(abi=abi_content, bytecode=bin_content)
    cfunc = contract.constructor(*arg_list)
    _, receipt = eth.invoke_contract_function(cfunc, 
                             emu_sender_address, emu_sender_key)

logging.info(f"Deployed contract address: " + str(receipt.contractAddress))

# Register the address to the Utility server
contract_info = dict()
contract_info['contract_name']    = emu_contract_name
contract_info['contract_address'] = str(receipt.contractAddress)
util_server = UtilityServerHelper(utility_url)
util_server.wait_for_server_ready()      # Block here until the server is ready
util_server.register_info(contract_info) # Register the contract address
logging.info("Contract address registered")

