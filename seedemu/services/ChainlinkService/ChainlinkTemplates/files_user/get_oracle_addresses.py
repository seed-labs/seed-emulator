#!/bin/env python3

import logging, json, os
from UtilityServerHelper import UtilityServerHelper


####################################################
util_server_url = "http://{util_server}:{util_server_port}"
oracle_contract_names = {oracle_contract_names}
link_contract_name    = "{link_contract_name}"
####################################################

# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

util_server = UtilityServerHelper(util_server_url)
util_server.wait_for_server_ready()

link_address  = util_server.get_contract_address(link_contract_name)

oracle_addresses = []
for oracle in oracle_contract_names:
    newname = 'oracle-' + oracle
    c_address = util_server.get_contract_address('oracle-' + oracle)
    oracle_addresses.append(c_address)

logging.info('Oracle contract addresses:' + str(oracle_addresses))
logging.info('Link contract address:    ' + link_address)

# Save this information to a file
data = dict()
data['oracle_contracts'] =  oracle_addresses
data['link_token_contract_address'] = link_address

# Save the addresses to a file 
directory = './info'
if not os.path.exists(directory):
    os.makedirs(directory)
with open(directory + '/contract_addresses.json', 'w') as f:
    json.dump(data, f)

