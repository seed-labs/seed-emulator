#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from seedemu import *
import time
import json
from test import SeedEmuTestCase
import requests


class GenesisTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.rpc_url = cls.get_eth_init_info()
        cls.rpc_port = 8545
        cls.contract_address = "0xA08Ae0519125194cB516d72402a00A76d0126Af8"
        cls.web3 = Web3(HTTPProvider(f"http://{cls.rpc_url}:{cls.rpc_port}"))
        cls.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return

    @classmethod
    def get_eth_init_info(cls):
        with open("./rpc_info.json") as f:
            data = json.load(f)
        return data["rpc_url"]

    # Test if the blockchain is up and running
    def test_poa_chain_connection(self):
        self.printLog("--------Starting POA Chain Connection Test--------")
        i = 1
        start_time = time.time()
        while True:
            self.printLog(f"Trial #{i}: Attempting to connect to POA chain.")
            if time.time() - start_time > 600:
                self.printLog("Time Exhausted: 600 seconds.")
                break
            try:
                if self.web3.isConnected():
                    self.printLog("Connection Successful.")
                    break
            except Exception as e:
                self.printLog(f"Connection Failed. Exception: {e}")
            time.sleep(20)
            i += 1
        self.assertTrue(self.web3.isConnected(), "Failed to connect to POA chain.")

    # Test using web3 if the contract is deployed on the blockchain
    def test_deployed_contract(self):
        self.printLog("Starting Deployed Contract Test")
        test_account = self.web3.eth.account.create()
        test_account_address = test_account.address
        test_account_private_key = test_account.privateKey.hex()
        self.printLog(f"Test Account Address: {test_account_address}")

        contract_address = self.web3.toChecksumAddress(self.contract_address)
        # Check if the contract is deployed on the blockchain
        start_time = time.time()
        while True:
            code = self.web3.eth.getCode(contract_address)
            self.printLog(f"Contract Code at Address: {code.hex()}")
            if code != "0x":
                self.printLog("Contract deployed successfully.")
                break
            if time.time() - start_time > 600:
                self.printLog("Time Exhausted: 600 seconds.")
                self.assertTrue(
                    False, "Contract not deployed on the blockchain within time limit."
                )
            time.sleep(5)
        self.assertTrue(code != "0x", "Contract not deployed on the blockchain.")

        # Load the ABI from the file
        abi_path = "./emulator-code/Contracts/Contract.abi"
        with open(abi_path, "r") as abi_file:
            contract_abi = json.load(abi_file)

        contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)
        self.printLog("Checking Total Supply of the Contract")
        expected_total_supply = 200000000000000000000000
        totalSupply = contract.functions.totalSupply().call()
        self.printLog(f"Total Supply: {totalSupply}")
        self.assertTrue(totalSupply == expected_total_supply, "Total Supply Mismatch")

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls("test_poa_chain_connection"))
        test_suite.addTest(cls("test_deployed_contract"))
        return test_suite


if __name__ == "__main__":
    test_suite = GenesisTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    GenesisTestCase.printLog("----------Test Summary----------")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    GenesisTestCase.printLog(
        "Score: {}/{} ({} errors, {} failures)".format(
            num - (errs + fails), num, errs, fails
        )
    )
