#!/bin/env python3

import logging, json, os
from UtilityServerHelper import UtilityServerHelper


####################################################
util_server_url = "http://{util_server}:{util_server_port}"
contract_name   = "oracle-" + "{node_name}"
####################################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Read the oracle contract address
with open('./info/oracle_contract_address.txt', 'r') as file:
    contract_address = file.read().strip()

data = dict()
data['contract_name']    = contract_name
data['contract_address'] = contract_address

util_server = UtilityServerHelper(util_server_url)
util_server.wait_for_server_ready() # Block here until the server is ready
util_server.register_info(data)     # Register the oracle contract address

