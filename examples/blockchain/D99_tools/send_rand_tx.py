#!/bin/env python3
# Send a raw transaction

import random, time, json
from web3 import Web3
from eth_account import Account



# Print balance
def print_balance(w, msg, account):
    print("{}: {} (account: {})".format(msg, w.getBalance(account), account))


def get_eth_balance(address):
    """Get ETH balance of an address"""
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0


def send_eth_transaction(from_account, to_address, amount_eth, nonce=None):
    """Send ETH transaction from one account to another"""
    try:
        # Convert amount to wei
        amount_wei = w3.toWei(amount_eth, 'ether')
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        
        # Standard ETH transfer gas limit
        gas_limit = 21000
        
        # Calculate total cost (amount + gas fees)
        total_cost = amount_wei + (gas_limit * gas_price)
        
        # Build transaction
        transaction = {
            'to': to_address,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce if nonce is not None else w3.eth.get_transaction_count(from_account.address),
            'chainId': 1337
        }
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, from_account.key)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash.hex()
    
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return None


# Connect to the blockchain
eth_node_url = 'http://10.153.0.71:8545'
w3 = Web3(Web3.HTTPProvider(eth_node_url))

Account.enable_unaudited_hdwallet_features()


# Generate the accouts
accounts = []
mnemonic = "gentle always fun glass foster produce north tail security list example gain"

total = 1000

'''
for i in range(total):
   path = f"m/44'/60'/0'/0/{i}"
   account = Account.from_mnemonic(mnemonic, account_path=path)
   #print("({}:{})".format(i, wallet.getBalance(account.address)))
   accounts.append(account)
'''

# Load the account addresses 
with open("prefunded_accounts.json", 'r') as file:
      accounts = json.load(file)

rounds = 10000000
wait_time = 0.1
for x in range(rounds):
   amount = random.randint(1, 10)/100

   sender_index = random.randint(0, total-1)
   recipt_index = random.randint(0, total-1) 
   while recipt_index == sender_index:
       recipt_index = random.randint(0, total-1) 

   print("----------------------------------------------------")
   print("{}: Sending {} ethers from {} to {}".format(x, amount, sender_index, recipt_index))
   
   # Select the sender and recipient
   sender = Account.from_key(accounts[sender_index]['private_key'])
   to_address = accounts[recipt_index]['address']
   print(sender.address)
   print(sender.key.hex())

   tx_hash = send_eth_transaction(sender, to_address, amount)
   if tx_hash:
       print(f"Real transaction sent! Hash: {tx_hash}")

   time.sleep(wait_time)   

