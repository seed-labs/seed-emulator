#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import requests
import logging
import json
import os


eth_url    = "http://{eth_server_ip}:{eth_server_http_port}"
faucet_url = "http://{faucet_ip}:{faucet_port}"


logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

web3 = Web3(HTTPProvider(eth_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)

web3.middleware_onion.inject(geth_poa_middleware, layer=0)
logging.info("Successfully connected to the Ethereum node.")

user_account    = web3.eth.account.create()
account_address = user_account.address
private_key     = user_account.privateKey.hex()

# Save user account information to a file
data = {{
    'account_address': account_address,
    'private_key': private_key
}}
with open('./info/user_account.json', 'w') as f:
    json.dump(data, f)
    
logging.info(f"User account address: {{account_address}}")


# Check if the faucet server is running for 600 seconds
def wait_for_faucet_server(timeout=-1)
    start_time = time.time()
    while True:
        try:
          response = requests.get(faucet_url)
          if response.status_code == 200:
              logging.info("faucet server connection succeed.")
              return 1

          logging.info("faucet server connection failed, retrying ...")
          time.sleep(10)  # wait for 10 seconds before retrying

          if timeout < 0:  # Wait forever 
              pass    
          else:
             if time.time() - start_time > timeout:
                logging.info("faucet server connection failed: 600 seconds exhausted.")
                return 0
        except Exception as e:
          pass

def send_fundme_request(account_address):
    data = {{'address': account_address, 'amount': 10}}
    logging.info(data)

    try:
       response = requests.post(faucet_url + "/fundme",
                     headers={{"Content-Type": "application/json"}}, 
                     data=json.dumps(data))
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

    except Exception as e:
	logging.error(f"An error occurred: {{str(e)}}")
	exit()

# Send /fundme request to faucet server
status = wait_for_faucet_server()

send_fundme_request(account_address)

deploy_contract(abifile='./contracts/user_contract.abi',
                binfile='./contracts/user_contract.bin')

def deploy_contract(abifile, binfile):
    with open(abifile, 'r') as abi_file:
    	user_contract_abi = abi_file.read()
    with open(binfine, 'r') as bin_file:
    	user_contract_bin = bin_file.read().strip()
    
    user_contract = web3.eth.contract(abi=user_contract_abi, 
                                      bytecode=user_contract_bin)
    
    # Deploy the user contract
    user_contract_data = user_contract.constructor().buildTransaction({{
        'from': account_address,
        'nonce': web3.eth.getTransactionCount(account_address),
        'gas': 3000000,
    }})['data']


def sendTransaction(recipient, amount, sender_name='', 
            gas=30000, nonce:int=-1, data:str='', 
            maxFeePerGas:float=3.0, maxPriorityFeePerGas:float=2.0, 
            wait=True, verbose=True):
    if nonce == -1:
        nonce = web3.eth.getTransactionCount(account_address)
    
    maxFeePerGas = Web3.toWei(maxFeePerGas, 'gwei')
    maxPriorityFeePerGas = Web3.toWei(maxPriorityFeePerGas, 'gwei')
    transaction = {{
        'nonce':    nonce,
        'from':     account_address,
        'to':       recipient,
        'value':    0,
        'chainId':  {chain_id},
        'gas':      gas,
        'maxFeePerGas':         maxFeePerGas,
        'maxPriorityFeePerGas': maxPriorityFeePerGas,
        'data':     data
    }}

    tx_hash = sendRawTransaction(private_key, transaction, wait, verbose)
    return tx_hash

def sendRawTransaction(key, transaction:dict, wait=True, verbose=True):
    signed_tx = web3.eth.account.sign_transaction(transaction, key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    if wait:
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash

tx_hash = sendTransaction(None, 0, '', gas=3000000, data=user_contract_data, wait=True, verbose=True)
contract_address = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300).contractAddress
logging.info(f"User contract deployed at address: {{contract_address}}")


# Save the contract address to a file
data = {{'contract_address': contract_address}}
with open('./info/user_contract.json', 'w') as f:
    json.dump(data, f)
