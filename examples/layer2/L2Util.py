#!/usr/bin/env python3
# encoding: utf-8

from web3 import Web3
import sys

# Monitor block using polling
def monitor_block(RPC):
    w3 = Web3(Web3.HTTPProvider(RPC))
    if not w3.isConnected():
        print("Failed to connect to RPC")
        return
    print(f"Connected to RPC: {RPC}")
    block_number = w3.eth.block_number
    print(f"Current block number: {block_number}")
    while True:
        new_block_number = w3.eth.block_number
        if new_block_number > block_number:
            # print block info in format string
            block = w3.eth.get_block(new_block_number)
            print(f"Block number: {block['number']}, timestamp: {block['timestamp']}, hash: {block['hash'].hex()}, tx count: {len(block['transactions'])}")
            print("Transaction hashes:")
            for tx in block['transactions']:
                print(f"  {tx.hex()}")
            block_number = new_block_number

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <ws>")
        sys.exit(1)
    ws = sys.argv[1]
    monitor_block(ws)