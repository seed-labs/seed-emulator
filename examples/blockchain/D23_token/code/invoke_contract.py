#!/bin/env python3

import os, json, logging, time, random, socket, sys
from web3 import Web3
from lib.FaucetHelper import FaucetHelper
from lib.EthereumHelper import EthereumHelper


##############################################
# Import global variables related to the emulator
from emulator_setup import *

CONTRACT = '../contract/SEEDToken20'
##############################################

def is_local_call(func):
   if func['stateMutability'] == 'view': 
       return True
   else
       return False

def convert_to_python_type(solidity_type):
    if solidity_type == 'address':
        return 'str'
    else: 
        return 'int' 

def get_function_from_abi(func_name, abi):
    for item in abi:
       if item['type'] == 'function' and item['name'] == func_name:
          return item

    assert False, "Function does not exist"


def construct_arg_list(func, argv):

    assert len(func['inputs']) == len(argv), "Length of argument do not match"

    arg_list = []
    i = 0
    for input_ in func['inputs']:
        python_type = convert_to_python_type(input_['type'])
        if python_type == 'int':
            arg_list.append(int(argv[i]))
        elif python_type == 'str':
            arg_list.append(str(argv[i]))
        elif python_type == 'bool':
            arg_list.append(bool(argv[i]))
        i += 1

    return arg_list


def print_balance(contract, address):
    print("---------------------------------------------")
    result = contract.functions.totalSupply().call()
    print("Total Supply: {}".format(result))
    result = contract.functions.balanceOf(address).call()
    print("Balance of {}: {}".format(address, result))


# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

length = len(sys.argv)
if len(sys.argv) < 2:
    print("Usage: invoke_contract function args ...")
    exit()


# Get data 
with open('./info.json', 'r') as f:
    data = json.load(f)   
account_address   = data['account_address']
key       = data['private_key']   
contract_address  = data['contract_address'] 

with open(CONTRACT + '.abi', 'r') as f:
     contract_abi = f.read()

eth  = EthereumHelper(chain_id=chain_id)
web3 = eth.connect_to_blockchain(eth_url, isPOA=True)
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

command = sys.argv[1]
argv    = sys.argv[2:]

#local_call(contract, command, argv)
#tx_call(contract, command, argv, account_address, account_key)

with open(CONTRACT + '.abi', 'r') as f:
    abi = json.load(f)

# Get the function information from the abi content (json)
func = get_function_from_abi(command, abi)

# Construct the arguments list 
arg_list = construct_arg_list(func, argv)

# Construct function
contract_func = contract.functions[func['name']](*arg_list)

# Invoke function
if is_local_call(func): 
    result = contract_func.call()
    print(result)
else: 
    _, receipt = eth.invoke_contract_function(contract_func, account_address, key)
    if receipt['status'] == 0:
        logging.error("Failed: invoke contract.")
    else:
        logging.info("Success: invoke the contract.")

