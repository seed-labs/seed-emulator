from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import logging
import time 
from sys import stderr


class EthereumHelper:

    _web: Web3
    _chain_id: int
    _max_fee:  float
    _max_priority_fee: float

    def __init__(self, chain_id:int=1337):
        """!
        @brief constructor.
        """

        self._chain_id = chain_id
        self._max_fee  = 3.0
        self._max_priority_fee = 2.0 

        return
    
    def __log(self, message: str):
        """!
        @brief log to stderr.

        @param message message.
        """
        print('== EthereumHelper: ' + message, file=stderr)


    def create_account(self):
        """!
        @brief Create an account
        @return account address and private ke
        """

        account = self._web3.eth.account.create()
        address = account.address
        key     = account.privateKey.hex()
        return address, key



    def connect_to_blockchain(self, url:str, isPOA=False, wait=True):
        """!
        @brief Connect to a blockchain node
        @param url The URL of the node (e.g., http://10.150.0.71:8545)
        @param isPOA Is the POA used for the consensus protocol (Proof-Of-Authority)?
        @returns Return self, for the purpose of API chaining.
        """

        self._url = url
        
        while True:
           self._web3 = Web3(Web3.HTTPProvider(url))
           if isPOA:
              self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

           if self._web3.isConnected():
              self.__log("Successfully connected to {}".format(url))
              break
           else: 
              if wait:
                 self.__log("Failed to connect to {}, retrying ...".format(url))
                 time.sleep(10)

        return self._web3


    def wait_for_blocknumber(self, block_number=5):
        """!
        @brief Wait for the blockchain to reach the specified block number
        """

        block_now = self._web3.eth.blockNumber
        while block_now < block_number:
            self.__log("Waiting for the block number to reach {} (current: {})".\
                        format(block_number, block_now))
            time.sleep(10)
            block_now = self._web3.eth.blockNumber


    def deploy_contract(self, contract_file, sender_address, sender_key, 
                        amount=0, gas=3000000, wait=True):
        """!
        @brief Deploy a smart contract

        @returns Return the transaction hash and the contract address.
        """
        with open(contract_file) as contract:
            data = contract.read()
            data = data.strip()

        tx_hash = self.send_raw_transaction(None, sender_address, sender_key,
                                           amount=amount, data=data, gas=gas) 
        rx_receipt = None
        if wait:
            tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        return tx_hash, tx_receipt

    def transfer_fund(self, receiver_address, sender_address, sender_key, 
                        amount=0, gas=3000000, wait=True):
        """!
        @brief Transfer fund to a receiver
        @param amount The unit is Ether
        @returns Return the transaction hash and receipt
        """

        tx_hash = self.send_raw_transaction(receiver_address, 
                                            sender_address, sender_key,
                                            amount=amount, gas=gas) 
        rx_receipt = None
        if wait:
            tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        return tx_hash, tx_receipt



    def send_raw_transaction(self, recipient, sender_address, sender_key,
                             data:str='', amount=0,  gas=300000): 
        """!
        @param amount The unit is Ether
        """

        transaction = {
            'nonce':    self._web3.eth.getTransactionCount(sender_address),
            'from':     sender_address,
            'to':       recipient,
            'value':    Web3.toWei(amount, 'ether'),
            'chainId':  self._chain_id,
            'gas':      gas,
            'maxFeePerGas':         Web3.toWei(self._max_fee, 'gwei'),
            'maxPriorityFeePerGas': Web3.toWei(self._max_priority_fee, 'gwei'), 
            'data':     data
        }

        signed_tx = self._web3.eth.account.sign_transaction(transaction, sender_key)
        tx_hash   = self._web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return tx_hash

    def invoke_contract_function(self, function, sender_address, sender_key,
                                 amount=0, gas=3000000, wait=True):
        """!
        @brief Invoke a contract function via a transaction.

        @param function The pre-built function 
        @param amount The unit is Ether
        @param wait Wait for the transaction receipt

        @returns Return the transaction hash.
        """

        assert self._web3 is not None
        assert function is not None

        transaction_info = {
            'nonce':    self._web3.eth.getTransactionCount(sender_address),
            'from':     sender_address,
            'value':    Web3.toWei(amount, 'ether'),
            'chainId':  self._chain_id,
            'gas':      gas,
            'maxFeePerGas':         Web3.toWei(self._max_fee, 'gwei'),
            'maxPriorityFeePerGas': Web3.toWei(self._max_priority_fee, 'gwei')
        }

        transaction = function.buildTransaction(transaction_info)
        signed_tx   = self._web3.eth.account.sign_transaction(transaction, sender_key)
        tx_hash     = self._web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        tx_receipt = None  
        if wait:
            tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        return tx_hash, tx_receipt

