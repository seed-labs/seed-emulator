#!/usr/bin/env python3
# encoding: utf-8

import time
import logging
import datetime
from SEEDBlockchain import Wallet

# Set your Ethereum node URL
eth_node_url = 'http://10.153.0.71:8545'

# Setup logging to file with timestamp
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"get_block_number_{timestamp}.log"
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(message)s',
	handlers=[logging.FileHandler(log_filename), logging.StreamHandler()]
)

# Create wallet and connect
wallet = Wallet(mnemonic="great amazing fun seed lab protect network system security prevent attack future")
wallet.connectToBlockchain(eth_node_url)

while True:
	block_number = wallet._web3.eth.block_number
	now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	msg = f"{now} - Current block number: {block_number}"
	logging.info(msg)
	time.sleep(10)
