#!/bin/env python3

import time, os, json, logging, sys
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware, construct_sign_and_send_raw_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
# from solcx import compile_files

CONTRACT_DIR = '/volumes/contract/'
RPC_URL = f'http://{sys.argv[1]}:8545'
DEPLOYER_ACC_KEY = '0x213c14e0aefb8738cda0bdccb2aa42d63ca9acfe32d9e666666bb2bce88b468f'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Compile the smart contract:
# compiledContract = compile_files(
#    [os.path.join(CONTRACT_DIR, 'IPFS_Storage.sol')],
#    output_values=['abi', 'bin'],
#    solc_version='0.8.15',
#    evm_version='london',
#    optimize=True,
#    optimize_runs=200
# )
# _, contract_interface = compiledContract.popitem()
# contract_abi = contract_interface['abi']
# contract_bin = contract_interface['bin']

# Load ABI
with open(os.path.join(CONTRACT_DIR, 'IPFS_Storage.abi')) as f:
    contract_abi = json.load(f)

# Load Bin
with open(os.path.join(CONTRACT_DIR, 'IPFS_Storage.bin')) as f:
    contract_bin = f.read()

# Connect to the Ethereum RPC API via Web3:
web3 = Web3(HTTPProvider(RPC_URL))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
retryInterval = 5
timeout = 60
while not web3.is_connected() and timeout > 0:
   logging.error("Failed to connect to Ethereum node. Retrying...")
   time.sleep(retryInterval)
   timeout -= retryInterval
logging.info("Successfully connected to the Ethereum node.")

# We will deploy this using an account that was created when the emulation was generated.
# This account has a starting balance of 9999999 ETH.
deployerAccount: LocalAccount = Account.from_key(DEPLOYER_ACC_KEY)
web3.middleware_onion.add(construct_sign_and_send_raw_middleware(deployerAccount))
web3.eth.default_account = deployerAccount.address

# Construct the smart contract object:
ipfsStorage = web3.eth.contract(abi=contract_abi, bytecode=contract_bin)
logging.info('Successfully imported ABI and bytecode to create contract.')

# Deploy the smart contract:
nonce = web3.eth.get_transaction_count(deployerAccount.address)
logging.info('Deploying smart contract...')
tx_hash = ipfsStorage.constructor().transact()
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
logging.info(f'Deployed smart contract at {tx_receipt.contractAddress}')

# Save the address of the deployed contract for our dApp to use:
with open('volumes/kubo-dapp/public/contract_address.txt', 'w') as file:
   file.write(tx_receipt.contractAddress)