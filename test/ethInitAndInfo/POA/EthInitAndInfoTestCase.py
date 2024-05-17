#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from seedemu import *
import time
from test import SeedEmuTestCase
import requests

class EthInitAndInfoTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.rpc_url, cls.faucet_url, cls.eth_init_node = cls.get_eth_init_info()
        cls.rpc_port = 8545
        cls.faucet_port = 80
        cls.eth_init_node_port = 5000
        cls.web3 = Web3(HTTPProvider(f"http://{cls.rpc_url}:{cls.rpc_port}"))
        cls.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return

    @classmethod
    def get_eth_init_info(self):
        with open('./eth_init_info.json') as f:
            data = json.load(f)
        return data['eth_node'], data['faucet'], data['eth_init_info']

    # Test if the blockchain is up and running
    def test_poa_chain_connection(self):
        self.printLog("Testing POA Chain Connection")
        i = 1
        current_time = time.time()
        while True:
            self.printLog("\n----------Trial {}----------".format(i))
            if time.time() - current_time > 600:
                self.printLog("TimeExhausted: 600 sec")
            try:
                self.assertTrue(self.web3.isConnected())
                self.printLog("Connection Succeed")
                break
            except Exception as e:
                self.printLog("Connection Failed trying again")
                time.sleep(20)
                i += 1
        self.assertTrue(self.web3.isConnected())
        
    # Test if the server is up
    def test_init_info_server_connection(self):
        self.printLog("Testing EthInitAndInfo Server Connection")
        url = f"http://{self.eth_init_node}:{self.eth_init_node_port}"
        i = 1
        current_time = time.time()
        while True:
            self.printLog("\n----------Trial {}----------".format(i))
            if time.time() - current_time > 600:
                self.printLog("TimeExhausted: 600 sec")
            try:
                response = requests.get(url)
                self.printLog("Connection Succeed: ", url)
                break
            except Exception as e:
                self.printLog(e)
                time.sleep(20)
                i += 1
        self.assertTrue(response.status_code == 200)
        
    # Test if the server has deployed the contract using contract_info API
    def test_contract_info(self):
        self.printLog("Testing Contract Info")
        url = f"http://{self.eth_init_node}:{self.eth_init_node_port}/contracts_info"
        try:
            current_time = time.time()
            while True:
                response = requests.get(url)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data:
                            self.printLog("Contract Info: ", data)
                            self.assertTrue(data['contract_name'] == 'test')
                            self.assertTrue(data['contract_address'] is not None)
                            break
                    except ValueError:
                        self.printLog("Invalid JSON received")
                else:
                    self.printLog(f"Non-200 status code received: {response.status_code}")

                if time.time() - current_time > 600:
                    self.printLog("TimeExhausted: 600 sec")
                    break
                time.sleep(5)
        except Exception as e:
            self.printLog(e)
    
    def fund_account(self, account_address):
        url = f"http://{self.faucet_url}:{self.faucet_port}/fundme"
        data = {
            "address": account_address,
            "amount": 10
        }
        
        current_time = time.time()
        while True:
            try:
                response = requests.post(url, headers={"Content-Type": "application/json"}, json=data)
                self.printLog(response)
                if response.status_code == 200:
                    api_response = response.json()
                    message = api_response.get('message', '')
                    if message:
                        self.printLog(f"Success: {message}")
                    else:
                        self.printLog("Funds request was successful but the response format is unexpected.")
                    break
            except requests.exceptions.RequestException as e:
                self.printLog(f"Request failed: {e}")
            
            if time.time() - current_time > 600:
                self.printLog("TimeExhausted: 600 sec")
                break
            time.sleep(5)

        # Check balance of the account
        current_time = time.time()
        while True:
            balance = self.web3.eth.getBalance(account_address)
            if balance > 0:
                self.printLog("Account funded successfully")
                break
            if time.time() - current_time > 100:
                self.printLog("TimeExhausted: 600 sec")
                break
            time.sleep(5)
        self.assertTrue(balance > 0)
    
    # Test using web3 if the contract is deployed on the blockchain
    def test_deployed_contract(self):
        self.printLog("Testing Deployed Contract")
        test_account = self.web3.eth.account.create()
        test_account_address = test_account.address
        test_account_private_key = test_account.privateKey.hex()

        self.printLog(f"Test Account Address: {test_account_address}")

        # Fund the test account with some ether
        self.fund_account(test_account_address)

        # Get contract address
        url = f"http://{self.eth_init_node}:{self.eth_init_node_port}/contracts_info?name=test"
        response = requests.get(url)
        self.printLog(f"Response Status Code: {response.status_code}")
        self.printLog(f"Response Content: {response.text}")

        if response.status_code == 200:
            try:
                data = response.json()
                contract_address = self.web3.toChecksumAddress(data)
                if contract_address:
                    current_time = time.time()
                    while True:
                        code = self.web3.eth.getCode(contract_address)
                        self.printLog(f"Contract Code at Address: {code.hex()}")
                        if code != '0x':
                            self.printLog("Contract is deployed successfully")
                            break
                        if time.time() - current_time > 600:
                            self.printLog("TimeExhausted: 600 sec")
                            break
                        time.sleep(5)

                    self.assertTrue(code != '0x')
                    
                    
                    # Load the ABI from the file
                    abi_path = "./emulator-code/Contracts/contract.abi"
                    with open(abi_path, 'r') as abi_file:
                        contract_abi =  json.load(abi_file)
                    
                    contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)
                    
                    # Check if the contract can receive funds
                    tx = {
                        'from': test_account_address,
                        'to': contract_address,
                        'value': self.web3.toWei(1, 'ether'),
                        'gas': 2000000,
                        'gasPrice': self.web3.toWei('50', 'gwei'),
                        'nonce': self.web3.eth.get_transaction_count(test_account_address),
                        'chainId': 1337,
                    }

                    signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=test_account_private_key)
                    tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    self.printLog(f"Transaction Hash: {tx_hash.hex()}")

                    receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
                    self.printLog(f"Transaction Receipt: {receipt}")

                    # Ensure the contract received funds
                    contract_balance = self.web3.eth.getBalance(contract_address)
                    self.printLog(f"Contract Balance: {self.web3.fromWei(contract_balance, 'ether')} Ether")
                    self.assertTrue(contract_balance > 0)
                else:
                    self.printLog("Contract address not found.")
                    self.assertTrue(False)
            except ValueError:
                self.printLog("Invalid JSON received")
                self.assertTrue(False)
        else:
            self.printLog(f"Non-200 status code received: {response.status_code}")
            self.assertTrue(False)

    # Register the contract using register_contract API and test if we can get the registered contract using contract_info API
    def test_api_call(self):
        self.printLog("Testing API Call")
        url = f"http://{self.eth_init_node}:{self.eth_init_node_port}/register_contract"
        data = {
            "contract_name": "api_test",
            "contract_address": "0x1234567890123456789012345678901234567890"
        }
        
        
    
    
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_poa_chain_connection'))
        test_suite.addTest(cls('test_init_info_server_connection'))
        test_suite.addTest(cls('test_contract_info'))
        test_suite.addTest(cls('test_deployed_contract'))
        return test_suite

if __name__ == "__main__":
    test_suite = EthInitAndInfoTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    EthInitAndInfoTestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    EthInitAndInfoTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
