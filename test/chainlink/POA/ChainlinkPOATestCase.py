#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from web3 import Web3
from seedemu import *
import time
from test import SeedEmuTestCase
import requests
import subprocess
import os

class ChainlinkPOATestCase(SeedEmuTestCase):
    def test_node_health(self, url: str):
        i = 1
        current_time = time.time()
        all_passing = False
        while True:
            self.printLog("\n----------Trial {}----------".format(i))
            if time.time() - current_time > 1200:
                self.printLog("TimeExhausted: 600 sec")
                break
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                all_passing = True
                for check in data['data']:
                    if check['attributes']['status'] != 'passing':
                        all_passing = False
                        self.printLog(f"Check failed: {check['attributes']['name']} - {check['attributes']['output']}")
                        break 
                if all_passing:
                    self.printLog("All checks are passing.")
                    break
                else:
                    self.printLog("Some checks are failing.")
            except Exception as e:
                self.printLog(e)
            
            time.sleep(20)
            i += 1
        
        self.assertTrue(all_passing)
    
    def test_chainlink_node_health(self):
        self.printLog("\n-----------Testing Chainlink Normal Node Health-----------")
        url = 'http://10.151.0.73:6688/health'
        self.test_node_health(url)
        
    def test_chainlink_init_node_health(self):
        self.printLog("\n-----------Testing Chainlink Init Node Health-----------")
        url = 'http://10.164.0.73:6688/health'
        self.test_node_health(url)
        
    def copy_file_from_docker(self, container_name, file_path_inside_container, host_destination_path):
        start_time = time.time()
        while time.time() - start_time < 1000: 
            try:
                subprocess.run(f"docker cp {container_name}:{file_path_inside_container} {host_destination_path}",
                            shell=True, check=True, text=True)
                if os.path.isfile(host_destination_path):
                    return host_destination_path
                else:
                    time.sleep(10)  
            except subprocess.CalledProcessError as e:
                time.sleep(10)
        
        self.fail("Failed to copy file from Docker container within 1000 seconds.")

        
    def test_link_token_deployment(self):
        self.printLog("\n-----------Testing Link Token Deployment-----------")
        try:
            container_name = 'as164h-Chainlink-0-10.164.0.73'
            file_path_inside_container = '/contracts/link_token_address.txt'
            host_destination_path = './link_token_address.txt'
            
            copied_file_path = self.copy_file_from_docker(container_name, file_path_inside_container, host_destination_path)
            
            with open(copied_file_path, 'r') as file:
                link_token_address = file.read().strip()
            
            w3 = Web3(Web3.HTTPProvider('http://10.150.0.71:8545'))
            assert w3.isConnected(), "Not connected to Ethereum node"
            
            abi_file_path = './emulator-code/resources/link_token.json'
            with open(abi_file_path, 'r') as abi_file:
                link_token_abi = json.load(abi_file)
            
            owner_address = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
            link_token_contract = w3.eth.contract(address=link_token_address, abi=link_token_abi)
            
            balance = link_token_contract.functions.balanceOf(owner_address).call()
            
            expected_balance = 1000000000000000000000000000
            assert balance == expected_balance, f"Owner's balance is incorrect, got: {balance}"
            self.printLog("Link Token deployed sucessfully.")
        except Exception as e:
            self.fail(f"Test failed due to an unexpected error: {e}")

        
        
    def test_oracle_contract_deployment(self):
        self.printLog("\n-----------Testing Oracle Contract Deployment-----------")
        container_name = 'as164h-Chainlink-0-10.164.0.73'
        file_path_inside_container = '/contracts/oracle_contract_address.txt'
        host_destination_path = './oracle_contract_address.txt'
        copied_file_path = self.copy_file_from_docker(container_name, file_path_inside_container, host_destination_path)
        
        link_token_address_path = os.path.expanduser('./link_token_address.txt')
        with open(copied_file_path, 'r') as file:
            oracle_contract_address = file.read().strip()

        with open(link_token_address_path, 'r') as file:
            expected_link_token_address = file.read().strip()
            
        w3 = Web3(Web3.HTTPProvider('http://10.150.0.71:8545'))
        self.assertTrue(w3.isConnected(), "Not connected to Ethereum node")

        abi_file_path = './emulator-code/resources/oracle_contract.json'  
        with open(abi_file_path, 'r') as abi_file:
            oracle_contract_abi = json.load(abi_file)

        oracle_contract = w3.eth.contract(address=oracle_contract_address, abi=oracle_contract_abi)

        # 1. Check if the owner is the expected address
        expected_owner_address = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
        actual_owner_address = oracle_contract.functions.owner().call()
        self.assertEqual(actual_owner_address.lower(), expected_owner_address.lower(), "Owner address does not match")
        self.printLog("Oracle Contract :::::: Owner address matches")

        # 2. Check if getChainlinkToken returns the expected LINK token address
        actual_link_token_address = oracle_contract.functions.getChainlinkToken().call()
        self.assertEqual(actual_link_token_address.lower(), expected_link_token_address.lower(), "LINK token address does not match")
        self.printLog("Oracle Contract :::::: LINK token address matches")


    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_chainlink_node_health'))
        test_suite.addTest(cls('test_chainlink_init_node_health'))
        test_suite.addTest(cls('test_link_token_deployment'))
        test_suite.addTest(cls('test_oracle_contract_deployment'))
        return test_suite
    
if __name__ == "__main__":
    test_suite = ChainlinkPOATestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ChainlinkPOATestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ChainlinkPOATestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
