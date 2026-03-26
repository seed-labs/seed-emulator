#!/bin/env python3
# Send ETH transaction, print status, and write detailed log with timestamped filename

import random
import time
import argparse
from web3 import Web3
from eth_account import Account
from datetime import datetime
import traceback
# --------------------------
# Parse command-line arguments
# --------------------------
# --------------------------
# Parse command-line arguments
# --------------------------
parser = argparse.ArgumentParser(description="ETH transaction sender")

parser.add_argument(
    "--ip",
    type=str,
    default="10.151.0.80",
    help="Ethereum node IP address"
)

parser.add_argument(
    "--port",
    type=int,
    default=8545,
    help="Ethereum node RPC port"
)

args = parser.parse_args()

# Build RPC URL
NODE_URL = f"http://{args.ip}:{args.port}"


# Connect to blockchain
w3 = Web3(Web3.HTTPProvider(NODE_URL))

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
log_file = f"transaction_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

def log_transaction(amount, from_addr, to_addr, tx_hash, status):
    """Append detailed transaction info to log file"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, "a") as f:
        f.write(f"{timestamp} | Amount: {amount} ETH | From: {from_addr} | To: {to_addr} | Hash: {tx_hash} | Status: {status}\n")

def send_eth_transaction(from_account, to_address, amount_eth):
    try:
        # 1. 检查发送者余额 (v5 使用 fromWei)
        balance_wei = w3.eth.get_balance(from_account.address)
        balance_eth = w3.fromWei(balance_wei, 'ether')
        
        amount_wei = w3.toWei(amount_eth, 'ether')
        gas_price = w3.eth.gas_price
        gas_limit = 21000
        
        if balance_wei < (amount_wei + (gas_price * gas_limit)):
            print(f"Skipping: Insufficient funds. Balance: {balance_eth} ETH")
            return None

        nonce = w3.eth.get_transaction_count(from_account.address)

        tx = {
            'to': to_address,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 1337  # 使用动态获取的 ID
        }

        # v5 使用 sign_transaction 和 rawTransaction
        signed_txn = w3.eth.account.sign_transaction(tx, from_account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"Transaction sent! Hash: {tx_hash.hex()}")

        print(f"Waiting for receipt (Max 20s)...")
        # 如果这里报错，traceback 会抓住它
        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=20,
            poll_latency=1
        )

        status = "Success" if receipt.status == 1 else "Fail"
        print(f"Transaction status: {status}\n")

        log_transaction(amount_eth, from_account.address, to_address, tx_hash.hex(), status)
        return tx_hash.hex()

    except Exception as e:
        print("\n" + "!"*60)
        print("ERROR DETECTED:")
        # 打印详细的报错行号和错误类型
        traceback.print_exc() 
        print("!"*60 + "\n")
        
        # 记录到日志
        log_transaction(amount_eth, from_account.address, to_address, "ERROR", str(e))
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

