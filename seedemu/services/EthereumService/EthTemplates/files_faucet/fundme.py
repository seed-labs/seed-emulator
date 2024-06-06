#!/bin/env python3

import time, sys, json
import requests
from eth_account import Account
import logging


#################################################
faucet_url      = "{faucet_url}"
faucet_fund_url = "{faucet_fund_url}"
#################################################

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get(faucet_url)
        if response.status_code == 200:
            logging.info("faucet server connection succeed.")
            break
        logging.info("faucet server connection failed: try again 10 seconds after.")
        
        time.sleep(10)
        if time.time() - start_time > timeout:
            logging.info("faucet server connection failed: 600 seconds exhausted.")
            exit()
    except Exception as e:
        pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	try:
		response = requests.post(faucet_fund_url, 
                        headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
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

if len(sys.argv) < 2:
   # Create a new account
   user_account = Account.create()
   account_address = user_account.address
   print(account_address)
else:
   account_address = sys.argv[1]

# Send fundme request to faucet server
send_fundme_request(account_address)

