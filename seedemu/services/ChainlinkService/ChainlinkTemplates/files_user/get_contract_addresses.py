#!/bin/env python3

import requests
import re
import logging
import time
import json
import os

def check_oracle_contracts(util_server_url, number_of_normal_servers):
    oracle_contracts_found = 0
    link_token_contract_address = None

    while oracle_contracts_found != number_of_normal_servers:
        try:
            response = requests.get(util_server_url)
            if response and response.status_code == 200:
                html_content = response.text

                oracle_contracts = re.findall(
                            r'<h1>Oracle Contract Address: (.+?)</h1>', html_content)
                oracle_contracts_found = len(oracle_contracts)
                logging.info(f"Checking for oracle contracts, found: {{oracle_contracts_found}}")

                match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)
                if match and match.group(1):
                    link_token_contract_address = match.group(1)
                    logging.info(f"Found Link Token address: {{link_token_contract_address}}")

                if oracle_contracts_found == number_of_normal_servers:
                    logging.info("Found all required oracle contracts.")
                    break
                else:
                    logging.info(f"Number of oracle contracts found ({{oracle_contracts_found}}) does not match the target ({{number_of_normal_servers}}). Retrying...")
            else:
                logging.warning("Failed to fetch data from server. Retrying...")

        except Exception as e:
            logging.error(f"An error occurred: {{e}}")

        # Wait 30 seconds before retrying
        time.sleep(30)

    return oracle_contracts, link_token_contract_address


# Change the work folder to where the program is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

util_server_url = "http://{util_server_ip}"
number_of_normal_servers = {number_of_normal_servers}
oracle_contracts, link_token_contract_address = check_oracle_contracts(
                     util_server_url, 
                     number_of_normal_servers)
logging.info(f"Oracle Contracts: {{oracle_contracts}}")
logging.info(f"Link Token Contract Address: {{link_token_contract_address}}")

# Save this information to a file
data = {{
    'oracle_contracts': oracle_contracts,
    'link_token_contract_address': link_token_contract_address
}}

directory = './info'
if not os.path.exists(directory):
    os.makedirs(directory)
    
with open('./info/contract_addresses.json', 'w') as f:
    json.dump(data, f)
