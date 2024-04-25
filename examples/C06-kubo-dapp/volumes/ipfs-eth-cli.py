#!/usr/bin/env python3

import os
from cmd import Cmd
from ipyfs import *
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware, construct_sign_and_send_raw_middleware

IPFS_HOST_IP = '10.150.0.250'
ETH_HOST_IP = '10.150.0.72'
CONTRACT_ADDRESS = None


class EthIpfsShell(Cmd):
    prompt = 'IPFS-ETH> '
    intro = 'Welcome to the IPFS-ETH console! Type ? to list commands.\n'

    def __init__(self, ethAPI, contract, *args, **kwargs):
        super(EthIpfsShell, self).__init__(*args, **kwargs)
        self.eth = ethAPI
        self.contract = contract

    def do_exit(self, _):
        '''Exit the application.'''
        return True
    
    def do_cat(self, _):
        '''Print stored file's contents to the screen.'''
        try:
            contents = cat(self.contract)
        except Exception as e:
            print(f'[ERROR] {type(e)}: {e}\n')
        else:
            print(f'Owner: {self.contract.functions.getOwner().call()}')
            print(f'Object CID: {self.contract.functions.getHash().call()}')
            print(f'{" CONTENTS ":=^50}\n{contents}\n{"="*50}')
            print()
        
    def do_download(self, _):
        '''Downloads the stored file to the current directory.'''
        try:
            hash = download(self.contract)
        except Exception as e:
            print(f'[ERROR] {type(e)}: {e}\n')
        else:
            print(f'[SUCCESS] object downloaded to local filesystem.')
            print(f'Owner: {self.contract.functions.getOwner().call()}')
            print(f'Object CID: {hash}')
            print()
    
    def do_upload(self, args):
        '''Uploads a local file to IPFS.'''
        filePath = args.strip()
        try:
            print(f'Attempting to upload "{filePath}" to IPFS...\n')
            hash = upload(self.eth, self.contract, filePath)
        except Exception as e:
            print(f'[ERROR] {type(e)}: {e}\n')
        else:
            print(f'[SUCCESS] {filePath} stored in IPFS at {hash}\n')
        
    def do_stats(self, _):
        print(f'Ethereum: connected to {ETH_HOST_IP}:8545')
        print(f'\tYour Address: {self.eth.eth.default_account}')
        print(f'\tSmart Contract: {self.contract.address}')

        ipfsId = Id(host=f'http://{IPFS_HOST_IP}', port=5001)
        print(f'IPFS: connected to {IPFS_HOST_IP}:5001')
        print(f'\tPeer ID: {ipfsId()["result"]["ID"]}')

        print()


def upload(w3, ethContract, filename:str) -> str:
    """
    @brief uploads a local file to the IPFS network, storing the hash in Etherum.
    @param api an instance of the IPFS API Client.
    @param filename the name and path of the file to be uploaded.
    """
    # Store on IPFS:
    ipfsAdd = Add(host=f'http://{IPFS_HOST_IP}', port=5001)
    with open(filename, 'rb') as f:
        info = ipfsAdd(file=f)['result']

    # Log with Ethereum smart contract:
    tx_hash = ethContract.functions.setHash(info['Hash']).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return info['Hash']

def cat(ethContract) -> str:
    # Get hash from Ethereum smart contract:
    hash = ethContract.functions.getHash().call()
    # tx_hash = ethContract.functions.getHash().transact()
    # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Get file from IPFS
    ipfsCat = Cat(host=f'http://{IPFS_HOST_IP}', port=5001)
    info = ipfsCat(path=hash)['result']

    return info

def download(ethContract) -> str:
    # Get hash from Ethereum smart contract:
    hash = ethContract.functions.getHash().call()

    with open(hash, 'wb') as f:
        # Get file from IPFS:
        ipfsGet = Get(host=f'http://{IPFS_HOST_IP}', port=5001)
        contents = ipfsGet(path=hash)['result']
        f.write(bytes(contents, 'utf-8'))
    
    return hash


def deployContract(w3:Web3):
    # Create smart contract:
    init_bytecode = open('bytecode', 'r').read()
    abi = open('abi', 'r').read()
    IPFS_Storage = w3.eth.contract(bytecode=init_bytecode, abi=abi)

    # Deploy smart contract:
    tx_hash = IPFS_Storage.constructor().transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    # receipt = w3.eth.get_transaction_receipt(tx_hash)
    contractAddr = receipt["contractAddress"]
    contract = w3.eth.contract(
        address=contractAddr,
        abi=abi
    )

    return contract

def initContract(w3:Web3):
    global CONTRACT_ADDRESS
    # Open ABI:
    abi = open('abi', 'r').read()

    # Deploy and/or initialize:
    if CONTRACT_ADDRESS:
        print(f'[INFO] Contract address from script: {CONTRACT_ADDRESS}')
    elif 'CONTRACT_ADDRESS' in os.environ:
        CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS')
        print(f'[INFO] Contract address from environment variable: {CONTRACT_ADDRESS}')
    else:
        try:
            CONTRACT_ADDRESS = open('CONTRACT_ADDRESS', 'r').read().strip()
        except:
            print(f'[INFO] Contract not found. Deploying a new one...')
            # Create and deploy:
            init_bytecode = open('bytecode', 'r').read()
            IPFS_Storage = w3.eth.contract(bytecode=init_bytecode, abi=abi)
            # Deploy smart contract:
            tx_hash = IPFS_Storage.constructor().transact()
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            # Export contract address for next time:
            CONTRACT_ADDRESS = receipt["contractAddress"]
            addrFile = open('CONTRACT_ADDRESS', 'w')
            addrFile.write(CONTRACT_ADDRESS)
            print(f'[INFO] Contract automatically deployed to {CONTRACT_ADDRESS}')
        else:
            print(f'[INFO] Contract address from file (previous run): {CONTRACT_ADDRESS}')

    # Initialize contract from address and ABI:
    contract = w3.eth.contract(
            address=CONTRACT_ADDRESS,
            abi=abi
    )

    return contract


if __name__ == "__main__":
    # Set up IPFS Connection:
    # ipfs = ipfsApi.Client(IPFS_HOST_IP, 5001)
    # ipfs = ipfshttpclient.connect(f'/ip4/{IPFS_HOST_IP}/tcp/5001/http')
    # ipfsFiles = Files(host=f'http://{IPFS_HOST_IP}', port=5001)
    ipfsId = Id(host=f'http://{IPFS_HOST_IP}', port=5001)
    # print(ipfsId())

    # Set up Ethereum connection & account:
    w3 = Web3(HTTPProvider(f'http://{ETH_HOST_IP}:8545'))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if 'ETH_PRIVATE_KEY' not in os.environ:
        print('ERROR: no private key found at ETH_PRIVATE_KEY environment variable.')
        exit(1)
    pk = os.environ.get('ETH_PRIVATE_KEY')
    acct = w3.eth.account.from_key(pk)
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(acct))
    w3.eth.default_account = acct.address  # Transactions that omit "from" will use this address.

    # Verify connections:
    if ipfsId()['result'] is not None and w3.is_connected():
        # Initialize and start an interactive shell:
        prompt = EthIpfsShell(w3, initContract(w3))
        prompt.cmdloop()
    else:
        print(f'IPFS: {"Connected to " + ipfsId()["result"]["ID"] if ipfsId() != None else "Disconnected"}')
        print(f'Ethereum: {"Connected" if w3.is_connected() else "Disconnected"}')