from web3 import Web3, exceptions, HTTPProvider
import json
import time
import requests
from web3.middleware import geth_poa_middleware
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class test_user_contract:
    url : str
    faucet_url : str
    web3 : Web3
    test_address: str
    private_key: str
    user_contract_abi_path: str
    user_contract_abi: dict
    
    def __init__(self):
        # Modify the next three lines based on the actual data
        self.rpc_url    = "http://10.160.0.72:8545"
        self.faucet_url = "http://10.160.0.74:80/fundme"
        self.user_contract_address = "0x7D34979B3D53c29f870180a8F426A4c843b0cF40"

        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.test_account = self.web3.eth.account.create()
        self.test_address = self.test_account.address
        self.private_key = self.test_account.privateKey.hex()
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
        
    def fund_test_account(self):
        data = {'address': self.test_address, 'amount': 1}
        response = requests.post(self.faucet_url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        if response.status_code == 200:
            logging.info(f"Successfully requested funds from faucet: {response.text}")
        if response.status_code != 200:
            logging.error(f"Failed to request funds from faucet: {response.text}")
            return False
        return True

    def check_eth_price(self):
        user_contract = self.web3.eth.contract(address=self.user_contract_address, abi=self.user_contract_abi)
        logging.info("Checking current ETH price in user contract")
        average_price = user_contract.functions.averagePrice().call()
        logging.info(f"Current ETH price in user contract: {average_price}")
        
        logging.info("Initiating a new request for ETH price data")
        self.user_contract_address = Web3.toChecksumAddress(self.user_contract_address)
   
        # Information about the API and path for logging purposes
        api = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
        path = "RAW,ETH,USD,PRICE"
        logging.info(f"API for ETH price: {api}")
        logging.info(f"Path for extracting price: {path}")

        request_eth_price_data_function = user_contract.functions.requestETHPriceData(api, path)
        tx = {
            'nonce': self.web3.eth.getTransactionCount(self.test_address),
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
        
        logging.info("Sleeping for 60 seconds to allow oracles to respond")
        time.sleep(60)
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
        logging.info(f"Updated ETH price: {average_price}")
        
    def run(self):
        if not self.is_blockchain_connected():
            return

        if not self.fund_test_account():
            return

        self.check_eth_price()


if __name__ == "__main__":
    test = test_user_contract()
    test.run()
