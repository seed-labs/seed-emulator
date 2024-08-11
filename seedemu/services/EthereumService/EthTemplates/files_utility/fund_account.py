#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
import requests
import logging
import json
from eth_account import Account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RPC_URL    = "http://{rpc_url}:{rpc_port}"
FAUCET_URL = "http://{faucet_url}:{faucet_port}"
DIR_PREFIX = "{dir_prefix}"

def connectEthNode():
    web3 = Web3(HTTPProvider(RPC_URL))
    while not web3.isConnected():
        logging.error("Failed to connect to Ethereum node. Retrying...")
        time.sleep(5)
        
    logging.info("Successfully connected to the Ethereum node.")
    return web3

def createAccount():
	new_account = Account.create()
	account_address = new_account.address
	private_key = new_account.privateKey.hex()
	saveAccountAsJson(new_account)
	return account_address, private_key

def saveAccountAsJson(account):
    # Data to be written to the JSON file
    acct = {{
        "address": account.address,
        "private_key": account.privateKey.hex()
    }}

    # File path where the JSON file will be saved
    file_path = DIR_PREFIX + '/account.json'

    # Write data to the JSON file
    with open(file_path, 'w') as file:
        json.dump(acct, file, indent=4)
	

# Check if the faucet server is running for 600 seconds
def isFaucetServerUp():
    timeout = 600
    start_time = time.time()
    while True:
        try:
            response = requests.get(FAUCET_URL)
            if response.status_code == 200:
                logging.info("faucet server connection succeed.")
                return True
            logging.info("faucet server connection failed: try again 10 seconds after.")
            
            time.sleep(10)
            if time.time() - start_time > timeout:
                logging.info("faucet server connection failed: 600 seconds exhausted.")
                return False
        except Exception as e:
            pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_url = "http://{faucet_url}:{faucet_port}/fundme"
	try:
		response = requests.post(request_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
		logging.info(response)
		if response.status_code == 200:
			api_response = response.json()
			message = api_response['message']
			if message:
				print(f"Success: {{message}}")
			else:
				logging.error("Funds request was successful but the response format is unexpected.")
		else:
			api_response = response.json()
			message = api_response['message']
			logging.error(f"Failed to request funds from faucet server. Status code: {{response.status_code}} Message: {{message}}")
			# Send another request
			logging.info("Sending another request to faucet server.")
			send_fundme_request(account_address)
	except Exception as e:
		logging.error(f"An error occurred: {{str(e)}}")
		exit()

def check_fund_result(web3, account_address):
    timeout = 100
    is_account_funded = False
    start = time.time()
    while time.time() - start < timeout:
        balance = web3.eth.get_balance(account_address)
        if balance > 0:
            is_account_funded = True
            break
        time.sleep(5)
    return is_account_funded

    

if __name__ == "__main__":
    web3 = connectEthNode()
    account_address, private_key = createAccount()

    if not isFaucetServerUp():
        exit()
    
    # Send /fundme request to faucet server
    send_fundme_request(account_address)
    is_account_funded = check_fund_result(web3, account_address)

    if is_account_funded:
        logging.info(f"Account funded: {{account_address}}")
    else:
        logging.error(f"Failed to fund account: {{account_address}}")
        exit()
