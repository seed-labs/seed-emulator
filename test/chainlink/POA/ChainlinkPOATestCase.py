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
import re
from SEEDBlockchain import Wallet

class ChainlinkPOATestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.wallet1 = Wallet(chain_id=1337)
        for name in ['Alice', 'Bob', 'Charlie', 'David', 'Eve']:
            cls.wallet1.createAccount(name)

        return
    
    def load_chainlink_data(self):
        try:
            with open('chainlink_data.json', 'r') as f:
                data = json.load(f)
            oracle_contracts = data.get('oracle_contracts', [])
            link_token_address = data.get('link_token_address', '')
            self.printLog("Chainlink data loaded from file.")
            return oracle_contracts, link_token_address
        except (FileNotFoundError, json.JSONDecodeError):
            oracle_contracts = []
            link_token_address = ''
            self.printLog("No chainlink data file found, starting with default values.")
    
    def test_node_health(self, url: str):
        self.printLog(f"Testing node health at {url}")
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
                    self.printLog("All checks are passing.\n")
                    break
                else:
                    self.printLog("Some checks are failing.\n")
            except Exception as e:
                self.printLog(e)
            
            time.sleep(20)
            i += 1
        
        self.assertTrue(all_passing)
        
    def get_oracle_chainlink_relationships(self, urls):
        credentials = {'email': 'seed@seed.com', 'password': 'Seed@emulator123'}
        headers = {'Content-Type': 'application/json'}
        all_addresses = []

        for base_url in urls:
            with requests.Session() as session:
                login_response = session.post(f'{base_url}/sessions', headers=headers, json=credentials)
                if login_response.status_code == 200:
                    print(f"Login successful for {base_url}")                    
                    jobs_response = session.get(f'{base_url}/v2/jobs')
                    contract_address = None
                    if jobs_response.status_code == 200:
                        jobs_data = jobs_response.json()['data']
                        contract_address = next((job['attributes']['directRequestSpec']['contractAddress'] for job in jobs_data if job['attributes'].get('directRequestSpec')), None)
                        if contract_address:
                            print(f"Contract address fetched from {base_url}: {contract_address}")
                        else:
                            print(f"No contract address found in the jobs for {base_url}")
                    else:
                        print(f"Failed to fetch job details from {base_url}: {jobs_response.text}")
                        
                    eth_address = None
                    eth_keys_response = session.get(f'{base_url}/v2/keys/eth')
                    if eth_keys_response.status_code == 200:
                        eth_keys_data = eth_keys_response.json()['data']
                        eth_address = eth_keys_data[0]['attributes']['address']
                        print(f"Chainlink Node address fetched from {base_url}: {eth_address}")
                    else:
                        print(f"Failed to fetch Ethereum keys from {base_url}: {eth_keys_response.text}")

                    if contract_address and eth_address:
                        all_addresses.append({
                            'url': base_url,
                            'chainlink_node_address': eth_address,
                            'contract_address': contract_address
                        })
                else:
                    print(f"Login failed for {base_url}: {login_response.text}")

        with open('all_addresses.json', 'w') as json_file:
            json.dump(all_addresses, json_file, indent=4)

        self.printLog("All addresses saved to all_addresses.json")
    
    def test_chainlink_node_health(self):
        asn = [150, 151, 152, 153, 154, 160, 161, 162]
        urls = ['http://10.{i}.0.73:6688'.format(i=i) for i in asn]
        self.printLog("\n-----------Testing Chainlink Normal Node Health-----------")
        for url in urls:
            self.test_node_health(url+ '/health')
        self.printLog("\n-----------Getting Chainlink - Oracle Relationships-----------")
        time.sleep(30)
        self.get_oracle_chainlink_relationships(urls)
        
    def wait_for_server_to_be_up(self, url, timeout=1000, interval=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return response
            except requests.ConnectionError:
                pass
            time.sleep(interval)
        raise Exception(f"Server at {url} did not come up within {timeout} seconds.")

    def test_chainlink_init_node_health(self):
        self.printLog("\n-----------Testing Chainlink Init Node Health-----------")
        url = 'http://10.164.0.73'
        response = self.wait_for_server_to_be_up(url, 1000, 10)
        html_content = response.text
        oracle_contracts = re.findall(r'<h1>Oracle Contract: (.+?)</h1>', html_content)
        self.printLog(f"Oracle contracts: {oracle_contracts}")
        expected_number_of_oracles = 8
        self.assertEqual(len(oracle_contracts), expected_number_of_oracles,
                        f"Expected {expected_number_of_oracles} oracle addresses, got {len(oracle_contracts)}")        
        match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)
        self.assertIsNotNone(match, "Link Token address not found in HTML content")
        link_token_address = match.group(1)
        if link_token_address:
            self.printLog(f"Link Token address: {link_token_address}")
        else:
            self.fail("Link Token address is not set.")

        data = {
            'oracle_contracts': oracle_contracts,
            'link_token_address': link_token_address
        }
        with open('chainlink_data.json', 'w') as f:
            json.dump(data, f)
        self.printLog("Chainlink data saved to file.")
        
    def test_link_token_deployment(self):
        self.printLog("\n-----------Testing Link Token Deployment-----------")
        link_token_address = self.load_chainlink_data()[1]
        try:            
            w3 = Web3(Web3.HTTPProvider('http://10.150.0.71:8545'))
            assert w3.isConnected(), "Not connected to Ethereum node"
            
            abi_file_path = './emulator-code/resources/link_token.json'
            with open(abi_file_path, 'r') as abi_file:
                link_token_abi = json.load(abi_file)
            
            owner_address = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
            self.printLog(f"Link Token owner address: {link_token_address}")
            link_token_address = Web3.toChecksumAddress(link_token_address)
            link_token_contract = w3.eth.contract(address=link_token_address, abi=link_token_abi)
            
            balance = link_token_contract.functions.balanceOf(owner_address).call()
            
            expected_balance = 1000000000000000000000000000
            assert balance == expected_balance, f"Owner's balance is incorrect, got: {balance}"
            self.printLog("Link Token deployed sucessfully.")
        except Exception as e:
            self.fail(f"Test failed due to an unexpected error: {e}")
    
    def test_oracle_contract_deployment(self):
        self.printLog("\n-----------Testing Oracle Contract Deployment-----------")
        oracle_contracts, link_token_address = self.load_chainlink_data()
        with open('all_addresses.json', 'r') as json_file:
            all_addresses_info = json.load(json_file)

        contract_to_eth_address = {info['contract_address'].lower(): info['chainlink_node_address'].lower() for info in all_addresses_info}
        for oracle_contract_address in oracle_contracts:
            self.printLog(f"------------------Test for Oracle Contract address: {oracle_contract_address} --------------------------")
            w3 = Web3(Web3.HTTPProvider('http://10.150.0.71:8545'))
            self.assertTrue(w3.isConnected(), "Not connected to Ethereum node")
            
            abi_file_path = './emulator-code/resources/oracle_contract.json'  
            with open(abi_file_path, 'r') as abi_file:
                oracle_contract_abi = json.load(abi_file)
            oracle_contract_address = Web3.toChecksumAddress(oracle_contract_address)
            oracle_contract = w3.eth.contract(address=oracle_contract_address, abi=oracle_contract_abi)

            # 1. Check if the owner is the expected address
            expected_owner_address = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
            actual_owner_address = oracle_contract.functions.owner().call()
            self.assertEqual(actual_owner_address.lower(), expected_owner_address.lower(), "Owner address does not match")
            self.printLog("Oracle Contract :::::: Owner address matches")

            # 2. Check if getChainlinkToken returns the expected LINK token address
            actual_link_token_address = oracle_contract.functions.getChainlinkToken().call()
            self.assertEqual(actual_link_token_address.lower(), link_token_address.lower(), "LINK token address does not match")
            self.printLog("Oracle Contract :::::: LINK token address matches")
            
            # 3. Check if the authorized sender is the expected Chainlink Ethereum address
            expected_eth_address = contract_to_eth_address.get(oracle_contract_address.lower())
            self.printLog(f"Expected Ethereum address for Oracle contract {oracle_contract_address}: {expected_eth_address}")
            if expected_eth_address:
                start_time = time.time()
                actual_sender_address = None
                while time.time() - start_time < 1000:
                    authorized_senders = oracle_contract.functions.getAuthorizedSenders().call()
                    if authorized_senders and authorized_senders[0]:
                        actual_sender_address = authorized_senders[0].lower()
                        break
                    else:
                        print("Authorized sender not found, retrying...")
                        time.sleep(10)

                if actual_sender_address:
                    self.printLog(f"Actual Chainlink Node address for Oracle contract {oracle_contract_address}: {actual_sender_address}")
                    self.assertEqual(actual_sender_address, expected_eth_address, "Authorized sender does not match Ethereum address")
                    self.printLog(f"Oracle Contract :::::: Authorized sender matches Chainlink Node address for {oracle_contract_address}\n")
                else:
                    self.fail(f"Failed to retrieve an authorized sender for {oracle_contract_address} within the timeout period")
            else:
                self.fail(f"No Ethereum address found for Oracle contract {oracle_contract_address}")
                
    def test_poa_chain_connection(self):
        url = 'http://10.150.0.71:8545'

        i = 1
        current_time = time.time()
        while True:
            self.printLog("\n----------Trial {}----------".format(i))
            if time.time() - current_time > 600:
                self.printLog("TimeExhausted: 600 sec")
            try:
                self.wallet1.connectToBlockchain(url, isPOA=True)
                self.printLog("Connection Succeed: ", url)
                break
            except Exception as e:
                self.printLog(e)
                time.sleep(20)
                i += 1
        self.assertTrue(self.wallet1._web3.isConnected())
    
    def check_chainlink_balance(self):
        chainlink_node_addresses = []
        with open('all_addresses.json', 'r') as f:
            all_addresses = json.load(f)
            chainlink_node_addresses = [address['chainlink_node_address'] for address in all_addresses]
            
        self.printLog("Chainlink Node addresses: ", chainlink_node_addresses)
        timeout = time.time() + 600
        
        for node_address in chainlink_node_addresses:
            balance_checked = False
            start_time = time.time()
            self.printLog(f"Checking balance for node {node_address}")
            while True:
                balance = self.wallet1.getBalance(node_address) 
                if balance > 0:
                    self.printLog(f"Balance for node {node_address} is {balance}ETH.")
                    self.assertTrue(balance > 0)
                    balance_checked = True
                    break
                elif time.time() > timeout:
                    self.printLog(f"Timed out: Balance for node {node_address} is not greater than 0 ETH after 600 seconds.")
                    break
                else:
                    time.sleep(5)
            
            self.assertTrue(balance_checked, f"Failed to confirm non-zero balance for node {node_address} within {(time.time() - start_time)} seconds.")

        self.printLog("Completed checking balances for all Chainlink node addresses.")
        
    
    # def test_user_contract(self):
    #     self.printLog("\n-----------Testing User Contract-----------")
    #     tx_hash = self.wallet1.deployContract('./emulator-code/resources/user_contract.bin')
        
        
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_chainlink_init_node_health'))
        test_suite.addTest(cls('test_chainlink_node_health'))
        test_suite.addTest(cls('test_link_token_deployment'))
        test_suite.addTest(cls('test_oracle_contract_deployment'))
        test_suite.addTest(cls('test_poa_chain_connection'))
        test_suite.addTest(cls('check_chainlink_balance'))
        return test_suite
    
if __name__ == "__main__":
    test_suite = ChainlinkPOATestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ChainlinkPOATestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ChainlinkPOATestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
