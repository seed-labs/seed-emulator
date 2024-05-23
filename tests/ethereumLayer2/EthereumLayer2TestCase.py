#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
import time

from web3 import Web3
from web3.middleware import signing
from web3.middleware import geth_poa_middleware
from web3.exceptions import TransactionNotFound

from tests import SeedEmuTestCase


class EthereumLayer2TestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.l1_chain_id = 1337
        cls.l2_chain_id = 42069
        cls.l1_url = "http://10.162.0.71:8545"
        cls.seq_url = "http://10.150.0.71:8545"
        cls.ns_urls = [f"http://10.{i}.0.71:8545" for i in range(151, 154)]
        cls.ns_urls[1] = "http://10.152.0.71:9545"
        cls.test_key_pair = (
            "0x2DDAaA366dc75119A256C41b9bd483D13A64389d",
            "0x4ba1ada11a1d234c3a03c08395c82e65320b5ae4aecca4a70143f4c157230528",
        )
        cls.test_acc = signing.private_key_to_account(cls.test_key_pair[1])

        cls.wait_until_all_containers_up(20)

    @classmethod
    def wait_until_connected(cls, url, timeout) -> bool:
        start = time.time()
        current = time.time()
        provider = Web3(Web3.HTTPProvider(url))

        while current - start < timeout:
            if provider.isConnected():
                break
            time.sleep(20)
            current = time.time()

        return provider.isConnected()

    def test_l1_node_connection(self):
        self.assertTrue(self.wait_until_connected(self.l1_url, 300))

    def test_sc_deployment(self):
        TIMEOUT = 600
        start = time.time()
        current = time.time()

        l1Provider = Web3(Web3.HTTPProvider(self.l1_url))
        self.assertTrue(l1Provider.isConnected())

        while current - start < TIMEOUT:
            code = l1Provider.eth.get_code("0x6f3f591D1e0e4a3ad649219a76763702933C6390")
            if code.hex() != "0x":
                break
            time.sleep(20)
            current = time.time()

        self.assertNotEqual(code.hex(), "0x")

    def test_seq_node_connection(self):
        self.assertTrue(self.wait_until_connected(self.seq_url, 600))

    def test_seq_node_status(self):
        provider = Web3(Web3.HTTPProvider(self.seq_url))
        self.assertTrue(provider.isConnected())

        bn1 = provider.eth.get_block_number()
        time.sleep(20)
        bn2 = provider.eth.get_block_number()
        self.assertGreater(bn2, bn1)

    def test_ns_node_synchronization(self):
        GAP = 100
        seq_provider = Web3(Web3.HTTPProvider(self.seq_url))
        self.assertTrue(seq_provider.isConnected())

        for ns_url in self.ns_urls:
            provider = Web3(Web3.HTTPProvider(ns_url))
            self.assertTrue(provider.isConnected())

            seq_bn = seq_provider.eth.get_block_number()
            ns_bn = provider.eth.get_block_number()
            self.assertLess(seq_bn - ns_bn, GAP)

    def test_chain_id(self):
        provider = Web3(Web3.HTTPProvider(self.seq_url))
        self.assertTrue(provider.isConnected())

        self.assertEqual(provider.eth.chain_id, self.l2_chain_id)

    def test_tx_execution(self):
        provider = Web3(Web3.HTTPProvider(self.seq_url))
        self.assertTrue(provider.isConnected())

        tx = self.test_acc.sign_transaction(
            {
                "chainId": self.l2_chain_id,
                "to": self.test_key_pair[0],
                "gas": 10**6,
                "gasPrice": Web3.toWei(10, "gwei"),
                "nonce": provider.eth.get_transaction_count(self.test_acc.address),
            }
        )
        txhash = provider.eth.send_raw_transaction(tx.rawTransaction)
        time.sleep(30)
        self.assertEqual(provider.eth.get_transaction_receipt(txhash)["status"], 1)

    def test_deposit(self):
        TIMEOUT = 180
        DEPOSIT_AMOUNT = Web3.toWei(1000, "ether")
        l1Provider = Web3(Web3.HTTPProvider(self.l1_url))
        self.assertTrue(l1Provider.isConnected())
        l2Provider = Web3(Web3.HTTPProvider(self.seq_url))
        self.assertTrue(l2Provider.isConnected())

        l2BalanceBefore = l2Provider.eth.get_balance(self.test_acc.address)

        tx = self.test_acc.sign_transaction(
            {
                "chainId": self.l1_chain_id,
                "to": "0x6f3f591D1e0e4a3ad649219a76763702933C6390",
                "gas": 10**7,
                "gasPrice": Web3.toWei(10, "gwei"),
                "value": DEPOSIT_AMOUNT,
                "nonce": l1Provider.eth.get_transaction_count(self.test_acc.address),
            }
        )
        txhash = l1Provider.eth.send_raw_transaction(tx.rawTransaction)

        start = time.time()
        current = time.time()
        while current - start < TIMEOUT:
            if (
                l2Provider.eth.get_balance(self.test_acc.address) - l2BalanceBefore
                == DEPOSIT_AMOUNT
            ):
                break
            time.sleep(16)
            current = time.time()

        self.assertEqual(l1Provider.eth.get_transaction_receipt(txhash)["status"], 1)

        l2BalanceAfter = l2Provider.eth.get_balance(self.test_acc.address)
        self.assertEqual(l2BalanceAfter - l2BalanceBefore, DEPOSIT_AMOUNT)

    def test_batch_submission(self):
        INBOX_ADDR = "0xff00000000000000000000000000000000042069".lower()
        BATCHER_ADDR = "0x9C1EA6d1f5E3E8aE21fdaF808b2e13698737643C".lower()
        TIMEOUT = 300
        TARGET_BATCH_COUNT = 3

        batchCount = 0
        start = time.time()
        current = time.time()

        l1Provider = Web3(Web3.HTTPProvider(self.l1_url))
        l1Provider.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.assertTrue(l1Provider.isConnected())

        while current - start < TIMEOUT:
            block = l1Provider.eth.get_block("latest", True)
            if len(block["transactions"]) > 0:
                for tx in block["transactions"]:
                    if (
                        tx["from"].lower() == BATCHER_ADDR
                        and tx["to"].lower() == INBOX_ADDR
                    ):
                        batchCount += 1
                        break
            if batchCount == TARGET_BATCH_COUNT:
                break
            time.sleep(16)
            current = time.time()

        self.assertEqual(batchCount, TARGET_BATCH_COUNT)

    def test_state_submission(self):
        OUTPUT_ORACLE_ADDR = "0x5Ab6Bc8FF05928FFd4c4D741d796A317Ab91E2B6"
        ABI = [
            {
                "type": "function",
                "name": "latestBlockNumber",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
                "stateMutability": "view",
            },
        ]
        TIMEOUT = 3600

        start = time.time()
        current = time.time()

        l1Provider = Web3(Web3.HTTPProvider(self.l1_url))
        self.assertTrue(l1Provider.isConnected())
        contract = l1Provider.eth.contract(abi=ABI, address=OUTPUT_ORACLE_ADDR)
        startBlock = contract.functions.latestBlockNumber().call()

        while current - start < TIMEOUT:
            currBlock = contract.functions.latestBlockNumber().call()
            if currBlock > startBlock:
                break
            time.sleep(16)

        self.assertGreater(currBlock, startBlock)

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()

        test_suite.addTest(cls("test_l1_node_connection"))
        test_suite.addTest(cls("test_sc_deployment"))
        test_suite.addTest(cls("test_seq_node_connection"))
        test_suite.addTest(cls("test_seq_node_status"))
        test_suite.addTest(cls("test_ns_node_synchronization"))
        test_suite.addTest(cls("test_chain_id"))
        test_suite.addTest(cls("test_deposit"))
        test_suite.addTest(cls("test_tx_execution"))
        test_suite.addTest(cls("test_batch_submission"))
        test_suite.addTest(cls("test_state_submission"))

        return test_suite


if __name__ == "__main__":
    test_suite = EthereumLayer2TestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    EthereumLayer2TestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    EthereumLayer2TestCase.printLog(
        "score: %d of %d (%d errors, %d failures)"
        % (num - (errs + fails), num, errs, fails)
    )
