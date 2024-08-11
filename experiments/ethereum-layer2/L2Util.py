#!/usr/bin/env python3
# encoding: utf-8

import sys
import time
import typing
import requests
import json

import web3

from web3 import Web3
from web3.middleware import signing
from web3.middleware import geth_poa_middleware
from web3.exceptions import TransactionNotFound

from hexbytes import HexBytes
from lib.services.EthereumLayer2Service import EthereumLayer2Account


class L2Util:
    __l1RPC: int
    __l2RPC: int
    __deployerURL: int
    __l1ChainId: int
    __l2ChainId: int
    __postfixL1Bridge = '/L1StandardBridgeProxy.json'
    __postfixInbox = "/getting-started.json"

    def __init__(self):
        config = L2Util._loadConfig()
        self.__l1RPC = f'http://localhost:{config["l1Port"]}'
        self.__l2RPC = f'http://localhost:{config["l2Port"]}'
        self.__deployerURL = (
            f'http://localhost:{config["deployerPort"]}'
        )
        self.__l1ChainId = config["l1ChainId"]
        self.__l2ChainId = config["l2ChainId"]

        self._testAcc = signing.private_key_to_account(
            json.loads(open("test_acc.json", "r").read())["privateKey"]
        )

    def monitorBlock(self, isL2: bool = True, RPC: str = None):
        _RPC = self.__l2RPC if isL2 else self.__l1RPC
        if RPC is not None:
            _RPC = RPC
        w3 = Web3(Web3.HTTPProvider(_RPC))
        if not w3.isConnected():
            print("Failed to connect to RPC")
            return
        if _RPC == self.__l1RPC:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        print(f"Connected to RPC: {_RPC}")
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

    def deposit(self, amountInETH=1):
        TIMEOUT = 120
        resp = requests.get(self.__deployerURL + self.__postfixL1Bridge)
        l1bridge = resp.json()["address"]

        l1Provider = Web3(Web3.HTTPProvider(self.__l1RPC))
        l2Provider = Web3(Web3.HTTPProvider(self.__l2RPC))
        if not l1Provider.isConnected() or not l2Provider.isConnected():
            print("Failed to connect to RPC")
            return
        l2BalanceBefore = l2Provider.eth.get_balance(self._testAcc.address)
        print(f"L1 balance before: {l1Provider.eth.get_balance(self._testAcc.address)}")
        print(f"L2 balance before: {l2BalanceBefore}")

        # Send transaction
        tx = {
            "chainId": self.__l1ChainId,
            "to": l1bridge,
            "value": l1Provider.toWei(amountInETH, "ether"),
            "gas": 10**7,
            "gasPrice": l1Provider.toWei(10, "gwei"),
            "nonce": l1Provider.eth.get_transaction_count(self._testAcc.address),
        }
        signed_tx = self._testAcc.sign_transaction(tx)
        tx_hash = l1Provider.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"L1 deposit transaction sent: {tx_hash.hex()}")

        print(f"Waiting for L2 transaction to be mined...")
        start = time.time()
        current = time.time()
        # Wait for transaction to be mined
        while current - start < TIMEOUT:
            l2BalanceAfter = l2Provider.eth.get_balance(self._testAcc.address)
            if l2BalanceAfter > l2BalanceBefore:
                break
            time.sleep(5)

        print(f"L1 balance after: {l1Provider.eth.get_balance(self._testAcc.address)}")
        print(f"L2 balance after: {l2BalanceAfter}")

    def sendL2Tx(self, to, value=0, data="0x", amount=1):
        TIMEOUT = 120

        l2Provider = Web3(Web3.HTTPProvider(self.__l2RPC))
        if not l2Provider.isConnected():
            print("Failed to connect to RPC")
            return

        # Send transaction
        tx_hashes = []
        for i in range(amount):
            tx = {
                "chainId": self.__l2ChainId,
                "to": to,
                "value": l2Provider.toWei(value, "ether"),
                "gas": 10**7,
                "gasPrice": l2Provider.toWei(1, "gwei"),
                "nonce": l2Provider.eth.get_transaction_count(self._testAcc.address) + i,
                "data": data,
            }
            signed_tx = self._testAcc.sign_transaction(tx)
            tx_hashes.append(l2Provider.eth.send_raw_transaction(signed_tx.rawTransaction))
            print(f"L2 transaction sent: {tx_hashes[-1].hex()}")

        print(f"Waiting for transaction to be mined...")
        start = time.time()
        current = start
        # Wait for transaction to be mined
        while current - start < TIMEOUT:
            try:
                receipts = []
                for tx_hash in tx_hashes:
                    receipt = l2Provider.eth.get_transaction_receipt(tx_hash)
                    if receipt is not None:
                        receipts.append(receipt)
                if len(receipts) == len(tx_hashes):
                    break
            except TransactionNotFound as e:
                pass
            time.sleep(5)
            current = time.time()

        print(f"Transaction receipts:")
        for receipt in receipts:
            print("=" * 70)
            print(json.dumps({k: v.hex() if isinstance(v, HexBytes) else v for k, v in dict(receipt).items()}, indent=2))
    
    def monitorBatch(self):
        resp = requests.get(self.__deployerURL + self.__postfixInbox)
        batchInbox = resp.json()["batchInboxAddress"]
        batchSender = resp.json()["batchSenderAddress"]
        print(f"Batch inbox: {batchInbox}")
        print(f"Batch sender: {batchSender}")

        w3 = Web3(Web3.HTTPProvider(self.__l1RPC))
        if not w3.isConnected():
            print("Failed to connect to RPC")
            return
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        print(f"Connected to RPC: {self.__l1RPC}")
        block_number = w3.eth.block_number
        print(f"Current block number: {block_number}")

        while True:
            new_block_number = w3.eth.block_number
            if new_block_number > block_number:
                block = w3.eth.get_block(new_block_number, True)
                for tx in block["transactions"]:
                    if tx["to"].lower() == batchInbox and tx["from"] == batchSender:
                        print("=" * 70)
                        print("New batch transaction:")
                        print(f"  Block number: {new_block_number}")
                        print(f"  Tx hash: {tx['hash'].hex()}")
                        print(f"  Data size: {len(tx['input'])}")
                        print(f"  Data:\n{tx['input']}")
                block_number = new_block_number

        

    def _loadConfig() -> typing.Dict[str, int]:
        with open("config.json", "r") as f:
            return json.loads(f.read())

def writeConfig(
    l1Port: int, l2Port: int, deployerPort: int, l1ChainId: int, l2ChainId: int
):
    with open("config.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "l1Port": l1Port,
                    "l2Port": l2Port,
                    "deployerPort": deployerPort,
                    "l1ChainId": l1ChainId,
                    "l2ChainId": l2ChainId,
                }
            )
        )

def generateAccounts() -> (
    typing.Dict[EthereumLayer2Account, typing.Tuple[str, str]]
):
    adminAcc = web3.Account.create()
    batcherAcc = web3.Account.create()
    proposerAcc = web3.Account.create()
    sequencerAcc = web3.Account.create()
    testAcc = web3.Account.create()

    with open("test_acc.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "address": testAcc.address,
                    "privateKey": testAcc.privateKey.hex(),
                }
            )
        )

    return {
        EthereumLayer2Account.GS_ADMIN: (
            adminAcc.address,
            adminAcc.privateKey.hex(),
        ),
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
    l2util = L2Util()

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <monitor/deposit/sendTx>")
        sys.exit(1)
    method = sys.argv[1]

    if method == "monitor":
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} monitor <block/batch>")
            sys.exit(1)
        if sys.argv[2] == "block":
            if len(sys.argv) < 4:
                print(f"Usage: {sys.argv[0]} monitor block <isL2: true/false> [custom RPC]")
                sys.exit(1)
            if len(sys.argv) == 4:
                l2util.monitorBlock(sys.argv[3] == "true")
            else:
                l2util.monitorBlock(sys.argv[3] == "true", sys.argv[4])
        elif sys.argv[2] == "batch":
            l2util.monitorBatch()
        else:
            print(f"Unknown monitor type: {sys.argv[2]}")
            sys.exit(1)
    elif method == "deposit":
        if len(sys.argv) < 2:
            print(
                f"Usage: {sys.argv[0]} deposit [amount in ether (default=1)]"
            )
            sys.exit(1)
        if len(sys.argv) == 2:
            l2util.deposit()
        else:
            l2util.deposit(sys.argv[2])

    elif method == "sendTx":
        if len(sys.argv) < 3:
            print(
                f"Usage: {sys.argv[0]} sendTx <to> [value in ether (default=0)] [data (default=0x)] [amount (default=1)]"
            )
            sys.exit(1)
        l2util.sendL2Tx(
            sys.argv[2],
            float(sys.argv[3]) if len(sys.argv) > 3 else 0,
            sys.argv[4] if len(sys.argv) > 4 else "0x",
            int(sys.argv[5]) if len(sys.argv) > 5 else 1,
        )
    else:
        print(f"Unknown method: {method}")
        sys.exit(1)
