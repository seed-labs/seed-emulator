#!/bin/env python3
# Send a raw transaction

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import os, sys
import json
import requests

def getFileContent(file_name):
    file = open(file_name, "r")
    data = file.read()
    file.close()
    return data.replace("\n","")

def getContent(file_name):
    file = open(file_name, "r")
    data = file.read()
    file.close()
    return data.replace("\n","")

# Connect to a geth node
def connect_to_geth(url, consensus):
  if   consensus==  'POA': 
        return connect_to_geth_poa(url)
  elif consensus == 'POS':
        return connect_to_geth_pos(url)
  elif consensus == 'POW':
        return connect_to_geth_pow(url)

# Connect to a geth node
def connect_to_geth_pos(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!") 
   return web3

# Connect to a geth node
def connect_to_geth_poa(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!") 
   web3.middleware_onion.inject(geth_poa_middleware, layer=0)
   return web3

# Connect to a geth node
def connect_to_geth_pow(url):
   web3 = Web3(Web3.HTTPProvider(url))
   if not web3.isConnected():
      sys.exit("Connection failed!")
   return web3


# Select an account address from the key store 
# Return: an address
def get_account_address(index):
   file_list = os.listdir('keystore/eth')
   if 'index.json' in file_list:
       file_list.remove('index.json')
   f = file_list[index]
   with open('keystore/eth/{}'.format(f)) as keyfile:
      content = json.loads(keyfile.read())
   return Web3.toChecksumAddress(content['address'])

# Return how many account addresses are in the keystore folder
def get_account_total():
   file_list = os.listdir('keystore/eth')
   if 'index.json' in file_list:
       file_list.remove('index.json')

   return len(file_list)


# Get all the account addresses from the key store
# Return: a list of addresses
def get_all_account_addresses():
   accounts = []
   file_list = os.listdir('keystore/eth')
   if 'index.json' in file_list:
       file_list.remove('index.json')

   for f in file_list:
      with open('keystore/eth/{}'.format(f)) as keyfile:
         content = json.loads(keyfile.read())
         if 'address' in content:
            accounts.append(Web3.toChecksumAddress(content['address'])) 
   return accounts

def get_all_accounts_with_node_info():
   f = open('keystore/eth/index.json')
   accounts = json.load(f)
   return accounts


# Print balance
def print_balance(web3, account):
    print("{}: {}".format(account, web3.eth.get_balance(account)))


# Construct a transaction
def construct_raw_transaction(sender, recipient, nonce, amount, data):
   tx = {
     'nonce': nonce,
     'from':  sender,
     'to':    recipient,
     'value': Web3.toWei(amount, 'ether'),
     'gas': 2000000,
     'chainId': 10,  # Must match with the value used in the emulator
     'gasPrice': Web3.toWei('50', 'gwei'),
     'data':  data
    }
   return tx

# Send raw transaction
def send_raw_transaction(web3, sender, recipient, amount, data):
   print("---------Sending Raw Transaction ---------------")
   nonce  = web3.eth.getTransactionCount(sender.address)
   tx = construct_raw_transaction(sender.address, recipient, nonce, amount, data)
   signed_tx  = web3.eth.account.sign_transaction(tx, sender.key)
   tx_hash    = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
   print("Transaction Hash: {}".format(tx_hash.hex()))

   tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
   print("Transaction Receipt: {}".format(tx_receipt))
   return tx_receipt

# Send raw transaction (no wait)
def send_raw_transaction_no_wait(web3, sender, recipient, amount, data):
   print("---------Sending Raw Transaction ---------------")
   nonce  = web3.eth.getTransactionCount(sender.address)
   tx = construct_raw_transaction(sender.address, recipient, nonce, amount, data)
   signed_tx  = web3.eth.account.sign_transaction(tx, sender.key)
   tx_hash    = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
   print("Transaction Hash: {}".format(tx_hash.hex()))
   return tx_hash


# Send transaction
def send_transaction_via_geth(node, recipient, amount, data):
   print("---------Sending Transaction from a geth node ---------------")
   tx_hash = node.eth.send_transaction({
         'from':  node.eth.coinbase,
         'to':    recipient,
         'value': amount,
         'data':  data})
   print("Transaction Hash: {}".format(tx_hash.hex()))

   tx_receipt = node.eth.wait_for_transaction_receipt(tx_hash)
   print("Transaction Receipt: {}".format(tx_receipt))
   return tx_receipt


# Deploy contract (high-level)
def deploy_contract_via_geth(node, abi_file, bin_file):
    print("---------Deploying Contract from a geth node ----------------")
    abi = getContent(abi_file)
    bytecode = getContent(bin_file)

    myContract = node.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = myContract.constructor().transact({ 'from':  node.eth.coinbase })
    print("... Waiting for block")
    tx_receipt = node.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print("Transaction Hash: {}".format(tx_receipt.transactionHash.hex()))
    print("Transaction Receipt: {}".format(tx_receipt))
    print("Contract Address: {}".format(contract_address))
    return contract_address



# Deploy contract (low-level): directly construct a transaction
# Using None as the target address, so the transaction will not have
# the 'to' field.
def deploy_contract_low_level_via_geth(node, abi_file, bin_file):
    print("---------Deploying Contract from a geth node (low level) ----------")
    bytecode = getContent(bin_file)
    tx_receipt = send_transaction_via_geth(node, None, 0, bytecode)
    contract_address = tx_receipt.contractAddress
    print("Contract Address: {}".format(contract_address))
    return contract_address


# Deploy a contract using raw transaction
def deploy_contract_raw(web3, sender, bin_file):
    print("---------Deploying Raw Contract (low level) ----------")
    bytecode = getContent(bin_file)
    tx_receipt = send_raw_transaction(web3, sender, None, 0, bytecode)
    contract_address = tx_receipt.contractAddress
    print("Contract Address: {}".format(contract_address))
    return contract_address


# Invoke contract
def invoke_contract_via_geth(node, contract_address, abi_file, function, arg):
    print("---------Invoking Contract Function via a geth node --------")
    new_address = Web3.toChecksumAddress(contract_address)
    contract = node.eth.contract(address=new_address, abi=getContent(abi_file))
    contract_func = contract.functions[function]

    # Invoke the function locally. We can immediately get the return value
    r = contract_func(arg).call()
    print("Return value: {}".format(r))

    # Invoke the function as a transaction. We cannot get the return value.
    # The function emits return value using an event, which is included in
    # the logs array of the transaction receipt.
    tx_hash = contract_func(arg).transact({ 'from':  node.eth.coinbase })
    tx_receipt = node.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction Hash: {}".format(tx_receipt.transactionHash.hex()))
    print("Transaction Receipt: {}".format(tx_receipt))
    return tx_receipt


# Send RPC to geth node 
def send_geth_rpc(url, method, params):
   myobj = {"jsonrpc":"2.0","id":1}
   myobj["method"] = method
   myobj["params"] = params

   x = requests.post(url, json = myobj)
   y = json.loads(x.text)
   return y["result"]

