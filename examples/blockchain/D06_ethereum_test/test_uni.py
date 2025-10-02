#!/usr/bin/env python3
# encoding: utf-8

import unittest
import time
import sys
from SEEDBlockchain import Wallet
from typing import List, Tuple
from web3 import Web3
import random
import logging
import datetime
import subprocess
import socket

class MnemonicTransactionTest(unittest.TestCase):
    """Test case for uni-directional transfer from random mnemonic account to random address"""
    interval = 10.0  # Default interval in seconds
    num_accounts = 5

    def setUp(self):
        """Setup connection to local Ethereum node and prepare accounts"""
        eth_host = '10.154.0.71'
        eth_port = 8545
    
        logging.info(f"Checking if {eth_host} is reachable...")
        try:
            ping_result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', eth_host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if ping_result.returncode != 0:
                self.fail(f"Host {eth_host} is not reachable. Check network connectivity.")
            logging.info(f"Checking if port {eth_port} is open on {eth_host}...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((eth_host, eth_port))
            s.close()
            if result != 0:
                self.fail(f"Port {eth_port} is not open on {eth_host}. Check if Ethereum node is running.")
            logging.info(f"Host {eth_host}:{eth_port} is reachable and port is open.")
            import platform
            logging.info(f"Python version: {sys.version}")
            logging.info(f"Platform: {platform.platform()}")
        except Exception as e:
            self.fail(f"Connection check failed: {str(e)}")
        try:
            logging.info("Creating wallet with mnemonic...")
            self.wallet = Wallet(mnemonic="great amazing fun seed lab protect network system security prevent attack future")
            logging.info(f"Connecting to Ethereum node at http://{eth_host}:{eth_port}...")
            logging.info("Attempting wallet connection...")
            try:
                self.wallet.connectToBlockchain(f'http://{eth_host}:{eth_port}')
                logging.info("Wallet connected successfully without POA middleware")
            except Exception as e1:
                self.fail(f"wallet connection failed: {str(e1)}")
            try:
                block_number = self.wallet._web3.eth.block_number
                logging.info(f"Wallet Web3 connection confirmed. Current block number: {block_number}")
            except Exception as e:
                self.fail(f"Wallet connected but basic RPC call failed: {str(e)}")
            logging.info("Creating accounts from mnemonic...")
            self.account_names = []
            for i in range(1, self.num_accounts + 1):
                name = f"Account{i}"
                self.wallet.createAccount(name)
                self.account_names.append(name)
            logging.info("Derived accounts:")
            for name in self.account_names:
                logging.info(f"  {name}: {self.wallet.getAccountAddressByName(name)}")
        except AssertionError as ae:
            self.fail(f"Blockchain connection failed: {str(ae)}")
        except Exception as e:
            self.fail(f"Setup failed: {str(e)}")

    def _ensure_account_funded(self, account_name):
        """Make sure the account has enough ETH for testing"""
        try:
            balance = self.wallet.getBalanceByName(account_name)
            logging.info(f"Current balance of {account_name}: {balance} ETH")
            if balance < 0.01:
                logging.warning(f"Account {account_name} needs funding (balance: {balance} ETH)")
                self.fail(f"Test requires {account_name} to have at least 0.01 ETH. Please fund the account manually.")
        except Exception as e:
            self.fail(f"Error checking or funding account: {str(e)}")
    
    def test_unidirectional_transfer(self):
        """Test: randomly pick a sender from 5 mnemonic accounts, randomly generate receiver, send transaction, verify success"""
        logging.info(f"Using transaction interval: {self.interval} seconds\n")

        # Pick a random sender
        sender_name = random.choice(self.account_names)
        sender_address = self.wallet.getAccountAddressByName(sender_name)
        logging.info(f"Randomly selected sender: {sender_name} ({sender_address})")

        # Randomly generate a receiver address (valid Ethereum address format)
        receiver_address = '0x' + ''.join(random.choices('0123456789abcdef', k=40))
        receiver_address = Web3.toChecksumAddress(receiver_address)
        logging.info(f"Randomly generated receiver: {receiver_address}")

        # Send ETH from sender to receiver
        transfer_amount = 0.01
        logging.info(f"Sending {transfer_amount} ETH from {sender_name} to {receiver_address}...")
        tx_hash = self.wallet.sendTransaction(
            recipient=receiver_address,
            amount=transfer_amount,
            sender_name=sender_name,
            wait=True,
            verbose=True
        )

        # Get transaction receipt to verify success
        receipt = self.wallet.getTransactionReceipt(tx_hash)
        self.assertTrue(receipt['status'], "Transaction failed")

        logging.info("Transaction succeeded!")

if __name__ == '__main__':
    # Set interval from command line argument if provided
    MnemonicTransactionTest.interval = 10

    # Setup logging to file with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"test_uni_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler(sys.stdout)]
    )

    while True:
        logging.info("\n--- Running test suite ---\n")
        unittest.main(exit=False)
        logging.info(f"Waiting {MnemonicTransactionTest.interval} seconds before next run...\n")
        time.sleep(MnemonicTransactionTest.interval)
