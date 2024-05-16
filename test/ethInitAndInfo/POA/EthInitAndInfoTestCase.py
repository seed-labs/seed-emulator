#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from web3 import Web3
from seedemu import *
import time
from test import SeedEmuTestCase
import requests

class EthInitAndInfoTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.rpc_url = None
        cls.faucet_url = None
        cls.eth_init_node = None

        return

    def get_eth_init_info(self):
        with open('./eth_init_info.json') as f:
            data = json.load(f)
        self.eth_init_node = data['eth_init_info']
        self.faucet_url = data['faucet']
        self.rpc_url = data['eth_node']

    def load_data(self):
        self.assertTrue(self.rpc_url)
        self.assertTrue(self.faucet_url)
        self.assertTrue(self.eth_init_node)

    # Test if the blockchain is up and running
    # def test_poa_chain_connection(self):
    #     url = 'http://
    # Test if the server is up
    # Test if the server has deployed the contract using contract_info API
    # Test using web3 if the contract is deployed on the blockchain
    # Register the contract using register_contract API and test if we can get the registered contract using contract_info API

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('load_data'))
        return test_suite

if __name__ == "__main__":
    test_suite = EthInitAndInfoTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    EthInitAndInfoTestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    EthInitAndInfoTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
