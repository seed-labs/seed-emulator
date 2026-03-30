#!/usr/bin/env python3
# encoding: utf-8

#from SEEDBlockchain import Wallet
from eth_account import Account
from web3 import Web3

def get_eth_balance(address):
    """Get ETH balance of an address"""
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.fromWei(balance_wei, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Error getting balance: {e}") 
        return 0 


# Set your Ethereum node URL
eth_node_url = 'http://10.153.0.71:8545'
w3 = Web3(Web3.HTTPProvider(eth_node_url))

Account.enable_unaudited_hdwallet_features()

for i in range(1000):
   mnemonic = "gentle always fun glass foster produce north tail security list example gain"
   path = f"m/44'/60'/0'/0/{i}"
   account = Account.from_mnemonic(mnemonic, account_path=path)
   print("({} ---  {})".format(account.address, get_eth_balance(account.address)))

