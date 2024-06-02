#!/bin/env python3

import requests
import re
import logging
import time
import json
import os


def get_contract_address(util_server_url, contract_name):
     url = util_server_url + "/contracts_info?name=" + contract_name  
     while (True):
        try:
            response = requests.get(url)
            if response and response.status_code == 200:
                address = response.text.strip().strip('"')
                break
            else:
                logging.warning("Failed to fetch data from server. Retrying...")
   
        except Exception as e:
               logging.error(f"An error occurred: {{e}}")
   
        # Wait 10 seconds before retrying
        time.sleep(10)

     return address


# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

util_server_url = "http://{util_server_ip}:{util_server_port}"
oracle_contract_names = {oracle_contract_names}
link_contract_name    = "{link_contract_name}"

oracle_addresses = []
for oracle in oracle_contract_names:
    newname = 'oracle-' + oracle
    oracle_addresses.append(get_contract_address(util_server_url, newname))

link_address  = get_contract_address(util_server_url, link_contract_name)

logging.info('Oracle contract addresses:' + str(oracle_addresses))
logging.info('Link contract address:' + link_address)

# Save this information to a file
data = {{
    'oracle_contracts': oracle_addresses,
    'link_token_contract_address': link_address
}}

directory = './info'
if not os.path.exists(directory):
    os.makedirs(directory)
    
with open('./info/contract_addresses.json', 'w') as f:
    json.dump(data, f)
