#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from web3 import Web3, exceptions
from seedemu import *
import time
from test import SeedEmuTestCase
import requests
import re
from SEEDBlockchain import Wallet

class ChainlinkPOATestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.asns = [150, 151, 152, 153, 154, 160, 161, 162, 163]
        cls.rpc_url = 'http://10.150.0.71:8545'
        cls.owner = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
        cls.owner_private_key = '20aec3a7207fcda31bdef03001d9caf89179954879e595d9a190d6ac8204e498'
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
            self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Successfully loaded Chainlink data.")
            return oracle_contracts, link_token_address
        except (FileNotFoundError, json.JSONDecodeError) as e:
            oracle_contracts = []
            link_token_address = ''
            self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error loading Chainlink data: {e}. Using default values.")

    def test_node_health(self, url: str):
        self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Starting node health check at {url}")
        i = 1
        current_time = time.time()
        all_passing = False
        while True:
            self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Trial {i}")
            if time.time() - current_time > 1200:
                self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Timeout reached after 20 minutes.")
                break
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                all_passing = True
                for check in data['data']:
                    if check['attributes']['status'] != 'passing':
                        all_passing = False
                        self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Health check failed: {check['attributes']['name']} - {check['attributes']['output']}")
                        break 
                if all_passing:
                    self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - All health checks passed.")
                    break
                else:
                    self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Detected failing checks, retrying...")
            except Exception as e:
                self.printLog(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Exception occurred during health check: {e}")
            
            time.sleep(20)
            i += 1
        
        self.assertTrue(all_passing)
        return all_passing

        
    def get_oracle_chainlink_relationships(self, urls):
        credentials = {'email': 'seed@seed.com', 'password': 'Seed@emulator123'}
        headers = {'Content-Type': 'application/json'}
        all_addresses = []

        for base_url in urls:
            self.printLog(f"Attempting to log in to {base_url}")
            with requests.Session() as session:
                login_response = session.post(f'{base_url}/sessions', headers=headers, json=credentials)
                if login_response.status_code == 200:
                    self.printLog(f"Login successful for {base_url}")
                    jobs_response = session.get(f'{base_url}/v2/jobs')
                    contract_address = None
                    if jobs_response.status_code == 200:
                        jobs_data = jobs_response.json().get('data', [])
                        if jobs_data:
                            contract_address = next((job['attributes'].get('directRequestSpec', {}).get('contractAddress') for job in jobs_data if job['attributes'].get('directRequestSpec')), None)
                            if contract_address:
                                self.printLog(f"Contract address fetched from {base_url}: {contract_address}")
                            else:
                                self.printLog(f"No contract address found in the jobs for {base_url}")
                        else:
                            self.printLog(f"No jobs data available in {base_url}")
                    else:
                        self.printLog(f"Failed to fetch job details from {base_url}: HTTP Status {jobs_response.status_code} - {jobs_response.text}")
                        
                    eth_address = None
                    eth_keys_response = session.get(f'{base_url}/v2/keys/eth')
                    if eth_keys_response.status_code == 200:
                        eth_keys_data = eth_keys_response.json().get('data', [])
                        if eth_keys_data:
                            eth_address = eth_keys_data[0].get('attributes', {}).get('address')
                            self.printLog(f"Chainlink Node Ethereum address fetched from {base_url}: {eth_address}")
                        else:
                            self.printLog(f"No Ethereum key data available in {base_url}")
                    else:
                        self.printLog(f"Failed to fetch Ethereum keys from {base_url}: HTTP Status {eth_keys_response.status_code} - {eth_keys_response.text}")

                    if contract_address and eth_address:
                        all_addresses.append({
                            'url': base_url,
                            'chainlink_node_address': eth_address,
                            'contract_address': contract_address
                        })
                else:
                    self.printLog(f"Login failed for {base_url}: HTTP Status {login_response.status_code} - {login_response.text}")

        if all_addresses:
            self.printLog("Saving all retrieved addresses to all_addresses.json")
            with open('all_addresses.json', 'w') as json_file:
                json.dump(all_addresses, json_file, indent=4)
            self.printLog(f"Successfully saved {len(all_addresses)} addresses.")
        else:
            self.printLog("No addresses were saved due to no successful data retrieval.")

    
    def test_chainlink_node_health(self):
        if not self.asns:
            self.printLog("No ASNs provided for testing Chainlink node health.")
            return

        urls = [f'http://10.{i}.0.73:6688' for i in self.asns]
        self.printLog("\n-----------Starting Tests on Chainlink Normal Nodes-----------")
        failed_nodes = []
        for url in urls:
            self.printLog(f"Testing node health for URL: {url}/health")
            if not self.test_node_health(url + '/health'):
                failed_nodes.append(url)
        
        if failed_nodes:
            self.printLog("Health check failed for the following nodes: " + ", ".join(failed_nodes))
        else:
            self.printLog("All Chainlink normal nodes passed the health check successfully.")

        self.printLog("\n-----------Testing Chainlink - Oracle Relationships-----------")
        self.printLog("Waiting 30 seconds before starting relationship tests...")
        time.sleep(30)
        self.printLog("Now retrieving Chainlink-Oracle relationships from nodes.")
        self.get_oracle_chainlink_relationships(urls)
        self.printLog("Completed Chainlink-Oracle relationship retrieval.")

        
    def __wait_for_server_to_be_up(self, url, timeout=1000, interval=10):
        self.printLog(f"Starting to check if server at {url} is up. Timeout set to {timeout} seconds.")
        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout:
            attempts += 1
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    self.printLog(f"Server at {url} is up and responding. Total time: {time.time() - start_time} seconds. Attempts: {attempts}")
                    return response
                else:
                    self.printLog(f"Server at {url} responded with status code {response.status_code}. Retrying in {interval} seconds.")
            except requests.ConnectionError as e:
                self.printLog(f"Attempt {attempts}: Connection to server at {url} failed. Retrying in {interval} seconds. Error: {e}")

            time.sleep(interval)

        self.printLog(f"Server at {url} did not come up within {timeout} seconds after {attempts} attempts.")
        raise Exception(f"Server at {url} did not come up within {timeout} seconds.")


    def test_chainlink_init_node_health(self):
        self.printLog("\n-----------Starting Chainlink Init Node Health Test-----------")
        url = 'http://10.164.0.73'
        self.printLog(f"Waiting for the server at {url} to be up...")
        response = self.__wait_for_server_to_be_up(url, 1000, 10)  # Wait for up to 1000 seconds, checking every 10 seconds.
        if response and response.status_code == 200:
            self.printLog(f"Server at {url} is now up. Proceeding with health checks.")
            start_time = time.time()
            elapsed_time = 0
            oracle_contracts = []
            expected_number_of_oracles = len(self.asns)
            link_token_address = ""

            while elapsed_time < 1000 and len(oracle_contracts) != expected_number_of_oracles:
                response = requests.get(url)
                if response.status_code == 200:
                    html_content = response.text
                    oracle_contracts = re.findall(r'<h1>Oracle Contract Address: (.+?)</h1>', html_content)
                    self.printLog(f"Checking for oracle contracts, found: {len(oracle_contracts)}")

                    if not link_token_address:
                        match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)
                        if match and match.group(1):
                            link_token_address = match.group(1)
                            self.printLog(f"Found Link Token address: {link_token_address}")
                time.sleep(10)
                elapsed_time = time.time() - start_time

            if len(oracle_contracts) == expected_number_of_oracles and link_token_address:
                data = {
                    'oracle_contracts': oracle_contracts,
                    'link_token_address': link_token_address
                }
                with open('chainlink_data.json', 'w') as f:
                    json.dump(data, f)
                self.printLog("Chainlink node data has been successfully saved to chainlink_data.json.")
            else:
                error_message = f"Failed to find the expected number of oracle contracts within the timeout. Expected {expected_number_of_oracles}, found {len(oracle_contracts)}."
                self.printLog(error_message)
                self.fail(error_message)
        else:
            self.printLog(f"Failed to receive a healthy response from {url}. Server may not be up or is not responding correctly.")

            
    def test_link_token_deployment(self):
        self.printLog("\n-----------Starting Link Token Deployment Test-----------")
        link_token_address = self.load_chainlink_data()[1]
        if not link_token_address:
            self.fail("Link Token address not found in configuration. Please ensure the Chainlink data is correctly set.")

        self.printLog(f"Loaded Link Token address: {link_token_address}")

        try:
            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            assert w3.isConnected(), "Failed to connect to Ethereum node at http://10.150.0.71:8545."
            self.printLog("Connected successfully to Ethereum node.")

            abi_file_path = './emulator-code/resources/link_token.json'
            with open(abi_file_path, 'r') as abi_file:
                link_token_abi = json.load(abi_file)
            self.printLog("Loaded ABI for Link Token.")

            owner_address = '0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9'
            self.printLog(f"Checking balance for Link Token owner at address: {owner_address}")
            
            link_token_address = Web3.toChecksumAddress(link_token_address)
            link_token_contract = w3.eth.contract(address=link_token_address, abi=link_token_abi)
            
            balance = link_token_contract.functions.balanceOf(owner_address).call()
            
            expected_balance = 1000000000000000000000000000  # 1 billion LINK (assuming 18 decimal places)
            assert balance == expected_balance, f"Unexpected balance for owner. Expected {expected_balance}, got {balance}"
            
            self.printLog("Link Token balance check passed successfully. Deployment is correct.")
        except AssertionError as err:
            self.fail(f"Assertion error in Link Token deployment test: {err}")
        except Exception as e:
            self.fail(f"Test failed due to an unexpected error: {e}")

    
    def test_oracle_contract_deployment(self):
        self.printLog("\n-----------Starting Oracle Contract Deployment Test-----------")
        oracle_contracts, link_token_address = self.load_chainlink_data()

        if not oracle_contracts:
            self.fail("No Oracle contracts found. Please ensure the Chainlink data is correctly set.")
        if not link_token_address:
            self.fail("Link Token address not found. Please ensure the Chainlink data is correctly set.")

        with open('all_addresses.json', 'r') as json_file:
            all_addresses_info = json.load(json_file)
            
        abi_file_path = './emulator-code/resources/oracle_contract.json'
        with open(abi_file_path, 'r') as abi_file:
            oracle_contract_abi = json.load(abi_file)
        self.printLog("Loaded ABI for Oracle Contract.")

        contract_to_eth_address = {info['contract_address'].lower(): info['chainlink_node_address'].lower() for info in all_addresses_info}

        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.assertTrue(w3.isConnected(), "Failed to connect to Ethereum node.")
        self.printLog("Connected successfully to Ethereum node.")
        for oracle_contract_address in oracle_contracts:
            self.printLog(f"Testing Oracle Contract at address: {oracle_contract_address}")
            oracle_contract_address = Web3.toChecksumAddress(oracle_contract_address)
            oracle_contract = w3.eth.contract(address=oracle_contract_address, abi=oracle_contract_abi)

            # 1. Check if the owner matches the expected address
            expected_owner_address = self.owner
            actual_owner_address = oracle_contract.functions.owner().call()
            self.assertEqual(actual_owner_address.lower(), expected_owner_address.lower(), "Owner address mismatch.")
            self.printLog("Owner address matches expected value.")

            # 2. Check if getChainlinkToken returns the expected LINK token address
            actual_link_token_address = oracle_contract.functions.getChainlinkToken().call()
            self.assertEqual(actual_link_token_address.lower(), link_token_address.lower(), "LINK token address mismatch.")
            self.printLog("LINK token address matches expected value.")

            # 3. Verify the expected Chainlink Ethereum address against the authorized sender
            expected_eth_address = contract_to_eth_address.get(oracle_contract_address.lower())
            self.assertIsNotNone(expected_eth_address, "No expected Ethereum address found for Oracle contract.")

            self.printLog(f"Verifying authorized sender for Oracle contract {oracle_contract_address}. Expected: {expected_eth_address}")
            actual_sender_address = self.__wait_for_authorized_sender_setup(oracle_contract)
            
            if actual_sender_address:
                self.assertEqual(actual_sender_address, expected_eth_address, "Authorized sender address mismatch.")
                self.printLog("Authorized sender matches expected Chainlink Node Ethereum address.")
            else:
                self.fail(f"Authorized sender for Oracle contract {oracle_contract_address} not found or does not match expected address.")

    def __wait_for_authorized_sender_setup(self, oracle_contract, timeout=1000, interval=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            authorized_senders = oracle_contract.functions.getAuthorizedSenders().call()
            if authorized_senders and authorized_senders[0]:
                return authorized_senders[0].lower()
            else:
                self.printLog("Authorized sender not found, retrying...")
                time.sleep(interval)
        return None

                
    def test_poa_chain_connection(self):
        url = self.rpc_url

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
    
    def test_chainlink_node_balance(self):
        chainlink_node_addresses = []
        with open('all_addresses.json', 'r') as f:
            all_addresses = json.load(f)
            chainlink_node_addresses = [address['chainlink_node_address'] for address in all_addresses]

        if not chainlink_node_addresses:
            self.fail("No Chainlink node addresses found. Please ensure 'all_addresses.json' contains valid data.")
        
        self.printLog(f"Initiating balance check for Chainlink Node addresses: {', '.join(chainlink_node_addresses)}")
        overall_start_time = time.time()
        timeout = overall_start_time + 600
        
        for node_address in chainlink_node_addresses:
            balance_checked = False
            start_time = time.time()
            self.printLog(f"Checking ETH balance for Chainlink Node at address {node_address}")

            while True:
                balance = self.wallet1.getBalance(node_address)
                if balance > 0:
                    elapsed_time = time.time() - start_time
                    self.printLog(f"Success: Node {node_address} has a balance of {balance} ETH (checked within {elapsed_time:.2f} seconds).")
                    balance_checked = True
                    break
                elif time.time() > timeout:
                    elapsed_time = time.time() - start_time
                    self.printLog(f"Timeout reached: Balance check for node {node_address} exceeded 600 seconds. Last checked balance: {balance} ETH (checked within {elapsed_time:.2f} seconds).")
                    break
                else:
                    if time.time() - start_time > 30:
                        self.printLog(f"Still waiting: Balance for node {node_address} remains at {balance} ETH after {(time.time() - start_time):.2f} seconds of checking.")
                    time.sleep(5)
            
            self.assertTrue(balance_checked, f"Balance check failed: Node {node_address} does not have a positive ETH balance after {(time.time() - start_time):.2f} seconds.")

        elapsed_overall_time = time.time() - overall_start_time
        self.printLog(f"Completed balance checks for all Chainlink node addresses in {elapsed_overall_time:.2f} seconds.")

        
    
    def test_user_contract(self):
        self.printLog("\n-----------Testing User Contract-----------")
        tx_hash = self.wallet1.deployContract('./emulator-code/resources/user_contract.bin')
        # self.printLog(f"User contract deployed with transaction hash: {web3.toHex(tx_hash)}")
        contract_address = self.wallet1.getContractAddress(tx_hash)
        self.printLog(f"User contract address: {contract_address}")
        
        
        # Check Web3 connection
        url = self.rpc_url
        web3 = Web3(Web3.HTTPProvider(url))

        if web3.isConnected():
            print("Connected to blockchain")
        else:
            print("Failed to connect to blockchain")
            exit(1)
            
        # Transfer some LINK tokens to the user contract
        abi_file_path = './emulator-code/resources/link_token.json'
        with open(abi_file_path, 'r') as abi_file:
            link_token_abi = json.load(abi_file)

        from_address = web3.toChecksumAddress(self.owner)
        to_address = web3.toChecksumAddress(Web3.toChecksumAddress(contract_address))
        amount = web3.toWei(100, 'ether')
        link_token_contract_address = self.load_chainlink_data()[1]
        link_contract = web3.eth.contract(address=link_token_contract_address, abi=link_token_abi)

        private_key = self.owner_private_key
        nonce = web3.eth.getTransactionCount(from_address)

        tx = {
            'nonce': nonce,
            'value': 0,
            'gas': 2000000,
            'gasPrice': web3.toWei('50', 'gwei')
        }
        
        tx_data = link_contract.functions.transfer(to_address, amount).buildTransaction(tx)
        signed_tx = web3.eth.account.signTransaction(tx_data, private_key)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        self.printLog(f"Transaction hash: {web3.toHex(tx_hash)}")
        
        
        # Wait for transaction to be mined
        timeout = 300
        check_interval = 10
        time_elapsed = 0
        transfer_link_receipt = None

        while not transfer_link_receipt and time_elapsed < timeout:
            try:
                transfer_link_receipt = web3.eth.getTransactionReceipt(tx_hash)
                self.printLog("Transaction receipt found")
            except exceptions.TransactionNotFound:
                print("Transaction not yet mined, waiting...")
                time.sleep(check_interval)
                time_elapsed += check_interval
        # Check if the transaction was successful and the LINK tokens were transferred
        balance = link_contract.functions.balanceOf(to_address).call()
        self.printLog(f"Balance of user contract: {balance}")
        self.assertTrue(balance > 0, "Failed to transfer LINK tokens to user contract")
        
        # Add the oracle contract addresses to the user contract
        user_contract_abi_path = './emulator-code/resources/user_contract_abi.json'
        with open(user_contract_abi_path, 'r') as abi_file:
            user_contract_abi = json.load(abi_file)
        user_contract_address = contract_address
        user_contract = web3.eth.contract(address=user_contract_address, abi=user_contract_abi)
        oracle_addresses = self.load_chainlink_data()[0]
        job_id = "7599d3c8f31e4ce78ad2b790cbcfc673"
        add_oracles_function = user_contract.functions.addOracles(oracle_addresses, job_id)
        add_oracles_tx = self.wallet1.invokeContract(add_oracles_function)
        self.printLog(f"Add oracles transaction hash: {web3.toHex(add_oracles_tx)}")
        add_oracles_receipt = None
        while not add_oracles_receipt:
            add_oracles_receipt = self.wallet1.getTransactionReceipt(add_oracles_tx)
            time.sleep(5)
        self.assertTrue(add_oracles_receipt, "Failed to add oracles")
        
        
        # Request ETH price data
        api = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
        path = "RAW,ETH,USD,PRICE"
        request_eth_price_data_function = user_contract.functions.requestETHPriceData(api, path)

        invoke_tx = self.wallet1.invokeContract(request_eth_price_data_function)
        self.printLog(f"Transaction hash: {web3.toHex(invoke_tx)}")

        receipt = None
        while not receipt:
            receipt = self.wallet1.getTransactionReceipt(invoke_tx)
            time.sleep(5)
        
        self.assertTrue(receipt)
        self.printLog("Request for ETH price data successful")
        
        self.printLog("Waiting 60 seconds for responses...")
        time.sleep(60)      
        responses_count = user_contract.functions.responsesCount().call()
        average_price = user_contract.functions.averagePrice().call()

        self.printLog(f"Responses count: {responses_count}")
        self.printLog(f"Average price: {average_price}")

        self.assertEqual(responses_count, len(self.asns), "Responses count is not equal")
        self.assertNotEqual(average_price, 0, "Average price is zero")

        
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_chainlink_init_node_health'))
        test_suite.addTest(cls('test_chainlink_node_health'))
        test_suite.addTest(cls('test_link_token_deployment'))
        test_suite.addTest(cls('test_oracle_contract_deployment'))
        test_suite.addTest(cls('test_poa_chain_connection'))
        test_suite.addTest(cls('test_chainlink_node_balance'))
        test_suite.addTest(cls('test_user_contract'))
        return test_suite
    
if __name__ == "__main__":
    test_suite = ChainlinkPOATestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ChainlinkPOATestCase.printLog("----------Test #%d--------=")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ChainlinkPOATestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
