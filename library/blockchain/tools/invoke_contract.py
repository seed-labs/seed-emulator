#!/bin/env python3

import os, json, logging, time, random, socket, sys
from web3 import Web3
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


eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)

# Get contract address
util_server = UtilityServerHelper(utility_url)
util_server.wait_for_server_ready()
contract_address = util_server.get_contract_address(emu_contract_name)


length = len(sys.argv)
if len(sys.argv) < 2:
    print("Usage: invoke_contract function args ...")
    exit()

func_name = sys.argv[1]
argv      = sys.argv[2:]

# Get the function information from the abi content (json)
abi_helper = ContractABIHelper(CONTRACT_ABI)

# Construct the arguments list based on the prototype of the function
arg_list = abi_helper.construct_arg_list(func_name, argv)

# Construct the contract and function
with open(CONTRACT_ABI, 'r') as f:
     abi_content = f.read()
contract = web3.eth.contract(address=contract_address, abi=abi_content)
contract_func = contract.functions[func_name](*arg_list)

# Invoke the function
if abi_helper.is_local_call(func_name): 
    result = contract_func.call()
    print(result)
else: 
    _, receipt = eth.invoke_contract_function(contract_func, 
                     emu_sender_address, emu_sender_key)
    if receipt['status'] == 0:
        logging.error("Failed: invoke contract.")
    else:
        logging.info("Success: invoke the contract.")

