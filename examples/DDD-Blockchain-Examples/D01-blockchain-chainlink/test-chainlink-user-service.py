from web3 import Web3, exceptions, HTTPProvider
import json
import time
import requests
import re
from web3.middleware import geth_poa_middleware
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class test_user_contract:
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
        self.rpc_url = "<RPC_URL>"
        self.user_contract_address = "<USER_CONTRACT_ADDRESS>"
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.test_account = self.web3.eth.account.create()
        self.test_address = self.user_account.address
        self.private_key = self.user_account.privateKey.hex()
        self.user_contract_abi_path = './contracts/user_contract.abi'
        self.user_contract_abi = self.load_user_contract()

    def load_user_contract(self):
        with open(self.user_contract_abi_path, 'r') as abi_file:
            user_contract_abi = json.load(abi_file)
        return user_contract_abi

    def is_blockchain_connected(self):
        try:
            self.web3.isConnected()
            return True
        except exceptions.ConnectionError:
            logging.error("Failed to connect to the blockchain")
            return False

    def check_eth_price(self):
        self.user_contract_address = Web3.toChecksumAddress(self.user_contract_address)
        user_contract = self.web3.eth.contract(address=self.user_contract_address, abi=self.user_contract_abi)
        logging.info("Checking ETH price")
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
        while True:
            if self.is_blockchain_connected():
                self.check_eth_price()
                break
            else:
                logging.error("Failed to connect to the blockchain. Retrying...")
                time.sleep(10)
                continue


if __name__ == "__main__":
    test = test_user_contract()
    test.run()