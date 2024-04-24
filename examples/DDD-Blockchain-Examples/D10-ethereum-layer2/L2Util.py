#!/usr/bin/env python3
# encoding: utf-8

import sys
import time
import os
import typing

import web3

from web3 import Web3
from web3.middleware import signing
from web3.exceptions import TransactionNotFound

from seedemu.services.EthereumLayer2Service import EthereumLayer2Account


L1_CHAIN_ID = 1337
L2_CHAIN_ID = 42069


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
            print("=" * 70)
            print(
                f"Block number: {block['number']}, timestamp: {block['timestamp']}, hash: {block['hash'].hex()}, tx count: {len(block['transactions'])}"
            )
            print("-" * 70)
            print("Transaction hashes:")
            print("." * 70)
            for tx in block["transactions"]:
                print(f"  {tx.hex()}")
                print("." * 70)
            print("-" * 70)
            block_number = new_block_number


def deposit(l1RPC, l2RPC, amountInETH=1):
    TEST_ACC = (os.getenv("TEST_ADDR"), os.getenv("TEST_PK"))
    TIMEOUT = 120

    acc = signing.private_key_to_account(TEST_ACC[1])
    l1Provider = Web3(Web3.HTTPProvider(l1RPC))
    l2Provider = Web3(Web3.HTTPProvider(l2RPC))
    if not l1Provider.isConnected() or not l2Provider.isConnected():
        print("Failed to connect to RPC")
        return
    l2BalanceBefore = l2Provider.eth.get_balance(acc.address)
    print(f"L1 balance before: {l1Provider.eth.get_balance(acc.address)}")
    print(f"L2 balance before: {l2BalanceBefore}")

    # Send transaction
    tx = {
        "chainId": L1_CHAIN_ID,
        "to": "0x6f3f591D1e0e4a3ad649219a76763702933C6390",
        "value": l1Provider.toWei(amountInETH, "ether"),
        "gas": 10**7,
        "gasPrice": l1Provider.toWei(10, "gwei"),
        "nonce": l1Provider.eth.get_transaction_count(acc.address),
    }
    signed_tx = acc.sign_transaction(tx)
    tx_hash = l1Provider.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"L1 deposit transaction sent: {tx_hash.hex()}")

    print(f"Waiting for L2 transaction to be mined...")
    start = time.time()
    current = time.time()
    # Wait for transaction to be mined
    while current - start < TIMEOUT:
        l2BalanceAfter = l2Provider.eth.get_balance(acc.address)
        if l2BalanceAfter > l2BalanceBefore:
            break
        time.sleep(5)

    print(f"L1 balance after: {l1Provider.eth.get_balance(acc.address)}")
    print(f"L2 balance after: {l2BalanceAfter}")


def sendL2Tx(l2RPC, to, value=0, data="0x"):
    TEST_ACC = (
        "0x2DDAaA366dc75119A256C41b9bd483D13A64389d",
        "0x4ba1ada11a1d234c3a03c08395c82e65320b5ae4aecca4a70143f4c157230528",
    )
    TIMEOUT = 120
    acc = signing.private_key_to_account(TEST_ACC[1])
    l2Provider = Web3(Web3.HTTPProvider(l2RPC))
    if not l2Provider.isConnected():
        print("Failed to connect to RPC")
        return

    # Send transaction
    tx = {
        "chainId": L2_CHAIN_ID,
        "to": to,
        "value": l2Provider.toWei(value, "ether"),
        "gas": 10**7,
        "gasPrice": l2Provider.toWei(1, "gwei"),
        "nonce": l2Provider.eth.get_transaction_count(acc.address),
        "data": data,
    }
    signed_tx = acc.sign_transaction(tx)
    tx_hash = l2Provider.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"L2 transaction sent: {tx_hash.hex()}")

    print(f"Waiting for transaction to be mined...")
    start = time.time()
    current = time.time()
    # Wait for transaction to be mined
    while current - start < TIMEOUT:
        try:
            receipt = l2Provider.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                break
        except TransactionNotFound as e:
            pass
        time.sleep(5)
        current = time.time()

    print(f"Transaction receipt: {receipt}")


def generateAccounts() -> typing.Dict[EthereumLayer2Account, typing.Tuple[str, str]]:
    adminAcc = web3.Account.create()
    batcherAcc = web3.Account.create()
    proposerAcc = web3.Account.create()
    sequencerAcc = web3.Account.create()
    testAcc = web3.Account.create()

    with open(".env", "w") as f:
        f.write(f"TEST_ADDR={testAcc.address}\n")
        f.write(f"TEST_PK={testAcc.privateKey.hex()}\n")

    return {
        EthereumLayer2Account.GS_ADMIN: (adminAcc.address, adminAcc.privateKey.hex()),
        EthereumLayer2Account.GS_BATCHER: (
            batcherAcc.address,
            batcherAcc.privateKey.hex(),
        ),
        EthereumLayer2Account.GS_PROPOSER: (
            proposerAcc.address,
            proposerAcc.privateKey.hex(),
        ),
        EthereumLayer2Account.GS_SEQUENCER: (
            sequencerAcc.address,
            sequencerAcc.privateKey.hex(),
        ),
        EthereumLayer2Account.GS_TEST: (testAcc.address, testAcc.privateKey.hex()),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <monitor/deposit/sendTx>")
        sys.exit(1)
    method = sys.argv[1]

    if method == "monitor":
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} monitor <l2RPC>")
            sys.exit(1)
        monitor_block(sys.argv[2])
    elif method == "deposit":
        if len(sys.argv) < 4:
            print(
                f"Usage: {sys.argv[0]} deposit <l1RPC> <l2RPC> [amount in ether (default=1)]"
            )
            sys.exit(1)
        if len(sys.argv) == 4:
            deposit(sys.argv[2], sys.argv[3])
        else:
            deposit(sys.argv[2], sys.argv[3], float(sys.argv[4]))

    elif method == "sendTx":
        if len(sys.argv) < 4:
            print(
                f"Usage: {sys.argv[0]} sendTx <l2RPC> <to> [value in ether (default=0)] [data (default=0x)]"
            )
            sys.exit(1)
        sendL2Tx(
            sys.argv[2],
            sys.argv[3],
            float(sys.argv[4]) if len(sys.argv) > 4 else 0,
            sys.argv[5] if len(sys.argv) > 5 else "0x",
        )
    else:
        print(f"Unknown method: {method}")
        sys.exit(1)
