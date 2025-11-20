#!/bin/env python3
# Send ETH transaction, print status, and write detailed log with timestamped filename

import random
import time
from web3 import Web3
from eth_account import Account
from datetime import datetime

# Connect to blockchain
eth_node_url = 'http://10.153.0.71:8545'
w3 = Web3(Web3.HTTPProvider(eth_node_url))

Account.enable_unaudited_hdwallet_features()

# Generate accounts
accounts = []
mnemonic = "gentle always fun glass foster produce north tail security list example gain"
total = 1000

print(f"Generating {total} accounts ...")
for i in range(total):
    path = f"m/44'/60'/0'/0/{i}"
    account = Account.from_mnemonic(mnemonic, account_path=path)
    accounts.append(account)

rounds = 10000000000
wait_time = 60  # seconds between transactions

# Log filename with timestamp
log_file = f"transaction_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

def log_transaction(amount, from_addr, to_addr, tx_hash, status):
    """Append detailed transaction info to log file"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, "a") as f:
        f.write(f"{timestamp} | Amount: {amount} ETH | From: {from_addr} | To: {to_addr} | Hash: {tx_hash} | Status: {status}\n")

def send_eth_transaction(from_account, to_address, amount_eth):
    try:
        amount_wei = w3.toWei(amount_eth, 'ether')
        gas_price = w3.eth.gas_price
        gas_limit = 21000
        nonce = w3.eth.get_transaction_count(from_account.address)

        tx = {
            'to': to_address,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 1337
        }

        signed_txn = w3.eth.account.sign_transaction(tx, from_account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"Transaction sent! Hash: {tx_hash.hex()}")

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        status = "Success" if receipt.status == 1 else "Fail"
        print(f"Transaction status: {status}\n")

        # Write detailed log
        log_transaction(amount_eth, from_account.address, to_address, tx_hash.hex(), status)

        return tx_hash.hex()

    except Exception as e:
        print(f"Error sending transaction: {e}")
        log_transaction(amount_eth, from_account.address, to_address, "N/A", f"Error: {e}")
        return None


for x in range(rounds):
    amount = random.randint(1, 10) / 10

    sender_index = random.randint(0, total - 1)
    recipt_index = random.randint(0, total - 1)
    while recipt_index == sender_index:
        recipt_index = random.randint(0, total - 1)

    sender = accounts[sender_index]
    to_address = accounts[recipt_index].address

    print("----------------------------------------------------")
    print(f"{x}: Sending {amount} ETH from accounts[{sender_index}] to accounts[{recipt_index}]")

    send_eth_transaction(sender, to_address, amount)

    print(f"Sleeping {wait_time} seconds...\n")
    time.sleep(wait_time)

