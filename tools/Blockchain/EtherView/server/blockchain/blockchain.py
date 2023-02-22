from flask import (
    Blueprint, flash, redirect, render_template, jsonify, request, Response, url_for, current_app as app
)
from web3 import Web3
import docker
import json
from .SEEDWeb3 import *
from eth_account import Account
from hexbytes import HexBytes

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


blockchain = Blueprint('blockchain', __name__)

# Get the balance of the 
@blockchain.route('/get_balance/', methods=('GET',))
def get_balance():
    web3  = connect_to_geth(app.web3_url, app.consensus)

    balance = {}
    for addr in app.eth_accounts:
        caddr = Web3.toChecksumAddress(addr)
        balance[addr] = web3.fromWei(web3.eth.get_balance(caddr), 'ether')

    for addr in app.local_accounts:
        caddr = Web3.toChecksumAddress(addr)
        balance[addr] = web3.fromWei(web3.eth.get_balance(caddr), 'ether')

    return balance

@blockchain.route('/get_balance_with_name/', methods=('GET',))
def get_balance_with_name():
    web3  = connect_to_geth(app.web3_url, app.consensus)

    balance = {}
    for addr in app.eth_accounts:
        node = {}
        caddr = Web3.toChecksumAddress(addr)
        node['balance']   = web3.fromWei(web3.eth.get_balance(caddr), 'ether')
        full_name = app.eth_accounts[addr]['name']
        node['node_name'] = app.eth_nodes[full_name]['displayname']
        balance[addr] = node

    for addr in app.local_accounts:
        node = {}
        caddr = Web3.toChecksumAddress(addr)
        node['balance']   = web3.fromWei(web3.eth.get_balance(caddr), 'ether')
        node['node_name'] = app.local_accounts[addr]['name']
        balance[caddr] = node

    return balance


@blockchain.route('/get_balance_of_account/<addr>', methods=('GET',))
def get_balance_of_account(addr):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    caddr = Web3.toChecksumAddress(addr)
    node = {}
    node['account'] = caddr
    node['balance'] = web3.fromWei(web3.eth.get_balance(caddr), 'ether')

    return node


# Get the signers for the last N blocks 
@blockchain.route('/get_signers/<lastN>', methods=('GET',))
def get_signers(lastN):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    latest = web3.eth.getBlock('latest').number
    start = latest - int(lastN) + 1
    if start <= 0:
       start = 1
    
    signers = {}
    for bk in range(start, latest+1):
       bkhash = web3.eth.getBlock(bk).hash
       result = send_geth_rpc(app.web3_url, "clique_getSigner", [bkhash.hex()])
       addr =  Web3.toChecksumAddress(result)

       name = app.eth_accounts[str(addr)]['name']
       container_id = app.eth_nodes[name]['container_id']
       
       signers[bk] = {'address': str(addr), 'container_name': name, 
                      'container_id': container_id}   

    return signers

# Get a transaction
@blockchain.route('/get_transaction/<txhash>', methods=('GET',))
def get_transaction(txhash):
    web3  = connect_to_geth(app.web3_url, app.consensus)

    try:
       tx = dict(web3.eth.get_transaction(txhash))
    except:
       tx = {"status": "No such transaction"}

    resp = Response(json.dumps(tx, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


# Get a transaction hash 
@blockchain.route('/get_transaction_receipt/<txhash>', methods=('GET',))
def get_transaction_receipt(txhash):
    web3  = connect_to_geth(app.web3_url, app.consensus)

    try:
       tx = dict(web3.eth.get_transaction_receipt(txhash))
    except:
       tx = {"status": "No such transaction"}

    resp = Response(json.dumps(tx, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp

# Get a block 
@blockchain.route('/get_block/<blockNumber>', methods=('GET',))
def get_block(blockNumber):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    if blockNumber == 'latest':
        blockNumber = web3.eth.getBlock('latest').number

    block = web3.eth.get_block(int(blockNumber))

    resp = Response(json.dumps(dict(block), cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@blockchain.route('/get_lastN_blocks/<lastN>', methods=('GET',))
def get_lastN_blocks(lastN):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    latest = web3.eth.getBlock('latest').number
    start = latest - int(lastN) + 1
    if start <= 0:
       start = 1

    blocks = {}
    for bk in range(start, latest+1):
       block = web3.eth.get_block(bk)
       blocks[bk] = dict(block)

    resp = Response(json.dumps(blocks, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@blockchain.route('/get_txs_from_block/<blockNumber>', methods=('GET',))
def get_txs_from_block(blockNumber):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    if blockNumber == 'latest':
        blockNumber = web3.eth.getBlock('latest').number

    block = web3.eth.get_block(int(blockNumber))
    transactions = {}
    for txhash in block.transactions:
        tx = web3.eth.get_transaction(txhash.hex())
        transactions[txhash.hex()] = dict(tx)

    resp = Response(json.dumps(transactions, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@blockchain.route('/get_tx_receipts_from_block/<blockNumber>', methods=('GET',))
def get_tx_receipts_from_block(blockNumber):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    if blockNumber == 'latest':
        blockNumber = web3.eth.getBlock('latest').number

    block = web3.eth.get_block(int(blockNumber))
    transactions = {}
    for txhash in block.transactions:
        tx = web3.eth.get_transaction_receipt(txhash.hex())
        transactions[txhash.hex()] = dict(tx)

    resp = Response(json.dumps(transactions, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@blockchain.route('/get_eth_nodes/', methods=('GET',))
def get_eth_nodes():
    return app.eth_nodes 

@blockchain.route('/get_base_fees/<lastN>', methods=('GET',))
def get_base_fees(lastN):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    latest = web3.eth.getBlock('latest').number
    start = latest - int(lastN) + 1
    if start <= 0:
       start = 1

    base_fees = {}
    for bk in range(start, latest+1):
       block = web3.eth.get_block(bk)
       #blocks[bk] = dict(block)
       tt = dict(block)
       base_fees[bk] = tt['baseFeePerGas']

    resp = Response(json.dumps(base_fees, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@blockchain.route('/get_gas_limits/<lastN>', methods=('GET',))
def get_gas_limits(lastN):
    web3  = connect_to_geth(app.web3_url, app.consensus)
    latest = web3.eth.getBlock('latest').number
    start = latest - int(lastN) + 1
    if start <= 0:
       start = 1

    gas_limits = {}
    for bk in range(start, latest+1):
       block = web3.eth.get_block(bk)
       tt = dict(block)
       gas_limits[bk] = tt['gasLimit']

    resp = Response(json.dumps(gas_limits, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@blockchain.route('/get_txpool_pending/', methods=('GET',))
def get_txpool_pending():
    pending = {}
    for node in app.eth_nodes: 
        node_info = app.eth_nodes[node]
        ip      = node_info['ip']
        url = "http://" + ip + ":8545"
        web3 = Web3(Web3.HTTPProvider(url))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        txpool = web3.geth.txpool.content()
        total = 0
        for key in txpool.pending:
           total += len(dict(txpool.pending[key]))
        pending[ip] = total

    resp = Response(json.dumps(pending, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@blockchain.route('/get_accounts')
def get_accounts():
    accounts =[]

    # Get the accounts from the emulator
    for address in app.eth_accounts:
        item = app.eth_accounts[address]
        accounts.append({"address": address,
                         "name":    item["name"],
                         "type":    "emulator"})

    # Generate local accounts using the mnemonic phrase. 
    Account.enable_unaudited_hdwallet_features()
    local_account_names = app.configure['local_account_names']
    for index in range(len(local_account_names)):
        account = Account.from_mnemonic(app.configure['mnemonic_phrase'], 
                     account_path=app.configure['key_derivation_path'].format(index))
        accounts.append({"address": account.address, 
                         "name":    local_account_names[index],
                         "type":    "local"})

    return accounts

@blockchain.route('/get_web3_providers')
def get_web3_providers():
    providers = []
    for key in app.eth_nodes: 
        node = app.eth_nodes[key]
        providers.append("http://%s:8545" % node['ip']) 

    return providers

@blockchain.route('/get_consensus')
def get_consensus():
    resp = Response(json.dumps(app.consensus, cls=HexJsonEncoder, indent=5))
    resp.headers['Content-Type'] = 'application/json'
    return resp
