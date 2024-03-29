from web3 import Web3, exceptions, HTTPProvider
import json
import time
import requests
import re
from web3.middleware import geth_poa_middleware
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class user_test:
    url : str
    faucet_url : str
    init_server_url : str
    link_token_contract_address : str = None
    oracle_contracts : list
    web3 : Web3
    owner_address: str
    private_key: str
    user_contract_abi_path: str
    user_contract_bin_path: str
    user_contract_abi: dict
    user_contract_bin: str
    
    def __init__(self):
        self.url = "http://10.164.0.71:8545"
        self.faucet_url = "http://128.230.212.249:3000/getEth"
        self.init_server_url = "http://10.164.0.73"
        self.web3 = Web3(Web3.HTTPProvider(self.url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.user_account = self.web3.eth.account.create()
        self.owner_address = self.user_account.address
        self.private_key = self.user_account.privateKey.hex()
        self.link_token_contract_address, self.oracle_contracts = self.fetch_init_data()
        self.user_contract_abi_path = './contracts/user_contract_abi.json'
        self.user_contract_bin_path = './contracts/user_contract.bin'
        self.user_contract_abi, self.user_contract_bin = self.load_user_contract()

        
    def fetch_init_data(self):
        response = requests.get(self.init_server_url)
        if response:
            if response.status_code == 200:
                html_content = response.text
                oracle_contracts = re.findall(r'<h1>Oracle Contract Address: (.+?)</h1>', html_content)
                logging.info(f"Checking for oracle contracts, found: {len(oracle_contracts)}")
                match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)
                if match and match.group(1):
                    link_token_contract_address = match.group(1)
                    logging.info(f"Found Link Token address: {link_token_contract_address}")
        return link_token_contract_address, oracle_contracts

    def is_blockchain_connected(self):
        try:
            self.web3.isConnected()
            return True
        except exceptions.ConnectionError:
            logging.error("Failed to connect to the blockchain")
            return False
        
    def fund_account(self):
        data = {"new_account": self.owner_address}
        response = requests.post(self.faucet_url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        if response.status_code != 200:
            logging.error(f"Failed to request funds from faucet: {response.text}")
            return False
        return True
        
    def is_account_funded(self):
        while True:
            balance = self.web3.eth.get_balance(self.owner_address)
            if balance > 0:
                logging.info(f"Address funded: {self.owner_address}")
                break
        return balance > 0

    def load_user_contract(self):
        with open(self.user_contract_abi_path, 'r') as abi_file:
            user_contract_abi = json.load(abi_file)
        with open(self.user_contract_bin_path, 'r') as bin_file:
            user_contract_bin = bin_file.read().strip()
        return user_contract_abi, user_contract_bin

    def deploy_user_contract(self):
        contract = self.web3.eth.contract(abi=self.user_contract_abi, bytecode=self.user_contract_bin)
        constructor_args = contract.constructor(self.link_token_contract_address).buildTransaction({
            'from': self.owner_address,
            'nonce': self.web3.eth.getTransactionCount(self.owner_address),
        })['data']
        txhash = self.sendTransaction(None, 0, '', gas=3000000, data=constructor_args, wait=True, verbose=True)
        contract_address = self.web3.eth.wait_for_transaction_receipt(txhash, timeout=300).contractAddress
        logging.info(f"User contract deployed at address: {contract_address}")
        return contract_address


    def sendRawTransaction(self, key, transaction:dict, wait=True, verbose=True):
        signed_tx = self.web3.eth.account.sign_transaction(transaction, key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        if wait:
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash

    def sendTransaction(self, recipient, amount, sender_name='', 
                gas=30000, nonce:int=-1, data:str='', 
                maxFeePerGas:float=3.0, maxPriorityFeePerGas:float=2.0, 
                wait=True, verbose=True):
        if nonce == -1:
            nonce = self.web3.eth.getTransactionCount(self.owner_address)
        
        maxFeePerGas = Web3.toWei(maxFeePerGas, 'gwei')
        maxPriorityFeePerGas = Web3.toWei(maxPriorityFeePerGas, 'gwei')

        transaction = {
            'nonce':    nonce,
            'from':     self.owner_address,
            'to':       recipient,
            'value':    0,
            'chainId':  1337,
            'gas':      gas,
            'maxFeePerGas':         maxFeePerGas,
            'maxPriorityFeePerGas': maxPriorityFeePerGas,
            'data':     data
        }

        tx_hash = self.sendRawTransaction(self.private_key, transaction, wait, verbose)
        return tx_hash

    def transfer_link_token(self, contract_address):
        logging.info("Starting LINK token transfer process")

        # Transfer LINK tokens to the user contract
        abi_file_path = './contracts/link_token.json'
        try:
            with open(abi_file_path, 'r') as abi_file:
                link_token_abi = json.load(abi_file)
        except Exception as e:
            logging.error(f"Failed to load ABI file: {e}")
            exit(1) 

        if self.link_token_contract_address:
            self.link_token_contract_address = self.web3.toChecksumAddress(self.link_token_contract_address)
            logging.info(f"Using LINK Token contract address: {self.link_token_contract_address}")
        else:
            logging.error("Link Token contract address not found. Please check the server response and the extraction logic.")
            exit(1) 

        nonce = self.web3.eth.getTransactionCount(self.owner_address)
        # Creating the transaction to get LINK tokens
        tx_get_link = {
            'from': self.owner_address,
            'to': self.link_token_contract_address,
            'nonce': nonce,
            'value': self.web3.toWei(1, 'ether'),
            'gas': 2000000,
            'gasPrice': self.web3.toWei('50', 'gwei'),
            'chainId': 1337
        }
        logging.info("Building transaction to acquire LINK tokens")

        signed_tx_get_link = self.web3.eth.account.signTransaction(tx_get_link, self.private_key)
        tx_hash_get_link = self.web3.eth.sendRawTransaction(signed_tx_get_link.rawTransaction)
        tx_receipt_get_link = self.web3.eth.waitForTransactionReceipt(tx_hash_get_link, timeout=300)
        logging.info(f"Transfer LINK to account transaction receipt: {tx_receipt_get_link}")

        link_contract = self.web3.eth.contract(address=self.link_token_contract_address, abi=link_token_abi)
        link_amount = self.web3.toWei(100, 'ether')
        transfer_function = link_contract.functions.transfer(contract_address, link_amount)

        tx_transfer = transfer_function.buildTransaction({
            'nonce': self.web3.eth.getTransactionCount(self.owner_address),
            'value': 0,
            'gas': 3000000,
            'gasPrice': self.web3.toWei('50', 'gwei'),
            'from': self.owner_address,
            'chainId': 1337
        })
        logging.info("Building transaction to transfer LINK tokens to the user contract")

        signed_tx_transfer = self.web3.eth.account.signTransaction(tx_transfer, self.private_key)
        tx_hash_transfer = self.web3.eth.sendRawTransaction(signed_tx_transfer.rawTransaction)
        tx_receipt_transfer = self.web3.eth.waitForTransactionReceipt(tx_hash_transfer, timeout=300)
        logging.info(f"Transfer LINK to user contract transaction receipt: {tx_receipt_transfer}")

        balance = link_contract.functions.balanceOf(contract_address).call()
        logging.info(f"Balance of user contract after transfer: {balance}")
        assert balance > 0, "Balance assertion failed: The user contract did not receive LINK tokens."

    def add_oracles_to_user_contract(self, contract_address):
        logging.info("Starting process to add oracle addresses to the user contract")

        user_contract_address = contract_address
        user_contract = self.web3.eth.contract(address=user_contract_address, abi=self.user_contract_abi)
        oracle_addresses = self.oracle_contracts
        logging.info(f"Oracle addresses to be added: {oracle_addresses}")
        job_id = "7599d3c8f31e4ce78ad2b790cbcfc673"
        logging.info(f"Job ID for oracle tasks: {job_id}")

        add_oracles_function = user_contract.functions.addOracles(oracle_addresses, job_id)
        tx = {
            'nonce': self.web3.eth.getTransactionCount(self.owner_address),
            'value': 0,
            'gas': 2000000,
            'gasPrice': self.web3.toWei('50', 'gwei')
        }

        add_oracles_tx = add_oracles_function.buildTransaction(tx)
        signed_tx = self.web3.eth.account.signTransaction(add_oracles_tx, self.private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        logging.info(f"Transaction to add oracles sent. Hash: {tx_hash.hex()}")

        add_oracles_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=300)
        if add_oracles_receipt.status == 1:
            logging.info("Successfully added oracle addresses to the user contract")
        else:
            logging.error("Failed to add oracle addresses to the user contract")

        assert add_oracles_receipt.status == 1, "Transaction to add oracles failed"

    def request_eth_price_data(self, contract_address):
        logging.info("Initiating request for ETH price data")

        user_contract_address = contract_address
        user_contract = self.web3.eth.contract(address=user_contract_address, abi=self.user_contract_abi)

        # Information about the API and path for logging purposes
        api = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
        path = "RAW,ETH,USD,PRICE"
        logging.info(f"API for ETH price: {api}")
        logging.info(f"Path for extracting price: {path}")

        request_eth_price_data_function = user_contract.functions.requestETHPriceData(api, path)
        tx = {
            'nonce': self.web3.eth.getTransactionCount(self.owner_address),
            'value': 0,
            'gas': 2000000,
            'gasPrice': self.web3.toWei('50', 'gwei')
        }

        # Building and sending transaction
        request_eth_price_data_tx = request_eth_price_data_function.buildTransaction(tx)
        signed_tx = self.web3.eth.account.signTransaction(request_eth_price_data_tx, self.private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        logging.info(f"Sent transaction for ETH price data request. Hash: {tx_hash.hex()}")

        request_eth_price_data_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        logging.info(f"Status of Transaction receipt for ETH price data request: {request_eth_price_data_receipt.status}")

        if request_eth_price_data_receipt.status == 1:
            logging.info("Request for ETH price data successful")
        else:
            logging.error("Failed to request ETH price data")

        logging.info("Waiting for responses from oracles")

        check_interval = 10
        while True:
            responses_count = user_contract.functions.responsesCount().call()
            if responses_count > 0:
                logging.info("Responses received from oracles")
                break
            else:
                logging.info("No responses received yet")
                time.sleep(check_interval)
        
        responses_count = user_contract.functions.responsesCount().call()
        average_price = user_contract.functions.averagePrice().call()
        logging.info(f"Responses count: {responses_count}")
        logging.info(f"Average ETH price: {average_price}")

        assert responses_count > 0 and average_price > 0, "No responses or price data received"
        
    
    def run(self):
        if not self.is_blockchain_connected():
            logging.error("Could not connect to the blockchain")
            exit(1)
        if not self.fund_account():
            logging.error("Failed to fund account")
            exit(1)
        if not self.is_account_funded():
            logging.error("Account not funded")
            exit(1)
        contract_address = self.deploy_user_contract()
        self.transfer_link_token(contract_address)
        self.add_oracles_to_user_contract(contract_address)
        self.request_eth_price_data(contract_address)
        

if __name__ == "__main__":
    user = user_test()
    user.run()