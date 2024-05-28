from flask import Flask, request, jsonify
from web3 import Web3
from web3.middleware import geth_poa_middleware
import sys, time
from hexbytes import HexBytes
import logging
import re
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
nonce_lock = threading.Lock()
MAX_FUND_AMOUNT = {max_fund_amount}

# Connect to a geth node
def connect_to_geth(url, consensus):
    if   consensus==  'POA': 
        return connect_to_geth_poa(url)
    elif consensus == 'POS':
        return connect_to_geth_pos(url)
    elif consensus == 'POW':
        return connect_to_geth_pow(url)

# Connect to a geth node
def connect_to_geth_pos(url):
    web3 = Web3(Web3.HTTPProvider(url))
    if not web3.isConnected():
        return ""
    return web3

# Connect to a geth node
def connect_to_geth_poa(url):
    web3 = Web3(Web3.HTTPProvider(url))
    if not web3.isConnected():
        return ""
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return web3

# Connect to a geth node
def connect_to_geth_pow(url):
    web3 = Web3(Web3.HTTPProvider(url))
    if not web3.isConnected():
        return ""
    return web3

# Construct a transaction
def construct_raw_transaction(sender, recipient, nonce, amount, data):
    tx = {{
        'nonce': nonce,
        'from':  sender,
        'to':    HexBytes(recipient),
        'value': Web3.toWei(amount, 'ether'),
        'gas': 2000000,
        'chainId': {chain_id},  # Must match with the value used in the emulator
        'gasPrice': Web3.toWei('50', 'gwei'),
        'data':  data
    }}
    return tx

def get_balance(web3, account):
    logging.info("--------- Checking Balance ---------")
    # Get the account balance in Wei
    balance_wei = web3.eth.get_balance(account)

    # Convert the balance from Wei to Ether
    balance_eth = web3.fromWei(balance_wei, 'ether')
    logging.info("Account: {{}}, Balance : {{}}".format(account, balance_eth))

    return balance_eth

# Send raw transaction
def send_raw_transaction_no_wait(web3, sender, sender_key, recipient, amount, nonce, data):
    try:
        logging.info("---------Sending Raw Transaction ---------------")
        tx = construct_raw_transaction(sender, recipient, nonce, amount, data)
        signed_tx  = web3.eth.account.signTransaction(tx, sender_key)
        tx_hash    = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        logging.info("Transaction Hash: {{}}".format(tx_hash.hex()))
        return tx_hash
    except ValueError as e:
        raise RuntimeError(f'Error sending transaction: {{e}}')

def wait_for_transaction_receipt(web3, tx_hash):
    try:
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        logging.info("Transaction Receipt: {{}}".format(tx_receipt))
        return tx_receipt
    except ValueError as e:
        raise RuntimeError(f'Error sending transaction: {{e}}')
        

def create_account(web3:Web3):
    # Generate a new Ethereum account
    account = web3.eth.account.create()
    return account


@app.route('/')
def index():
    return 'OK', 200

# Route for handling form submission
@app.route('/fundme', methods=['POST'])
def submit_form():
    if request.is_json:
        # If the request is JSON
        data = request.get_json()
        recipient = data.get('address')
        amount = data.get('amount')
    else:
        recipient = request.form.get('address')
        amount = request.form.get('amount')

    ip_address = request.remote_addr
    logging.info(f"recipient: {{recipient}} amount: {{amount}} sender ip: {{ip_address}}")
    
    # Check if 'recipient' is not None and follows the format of an Ethereum account
    if recipient is None:
        logging.info("address cannot be empty")
        return jsonify({{'status': 'error', 'message': 'address cannot be empty'}}), 500
    elif not re.match(r'^0x[a-fA-F0-9]{{40}}$', recipient):
        logging.info("Invalid Ethereum Address")
        return jsonify({{'status': 'error', 'message': 'Invalid Ethereum address'}}), 500

    if amount is None:
        logging.info("amount cannot be empty")
        return jsonify({{'status': 'error', 'message': 'amount cannot be empty'}}), 500
    # Check if 'amount' is a number and less than 10
    try:
        amount = int(amount)
        if amount < 0:
            logging.info("amount should be a number larger than 0")
            return jsonify({{'status': 'error', 'message': 'Amount should be a number larger than 0'}}), 500
        if amount > MAX_FUND_AMOUNT:
            logging.info("Amount should not be larger than max_fund_amount")
            return jsonify({{'status': 'error', 'message': f'Amount should not be larger max_fund_amount: {{MAX_FUND_AMOUNT}}'}}), 500
        if amount > get_balance(app.config['WEB3'], app.config['SENDER_ADDRESS']):
            logging.info("Request fund amount is larger than the Faucet account balance")
            return jsonify({{'status': 'error', 'message': 'Request fund amount is larger than the Faucet account balance.'}}), 500
    except ValueError:
        logging.info("amount should be a number")
        return jsonify({{'status': 'error', 'message': 'Amount should be a number'}}), 500
    
    # nonce = 1
    with nonce_lock:
        app.config['NONCE'] = max(app.config['NONCE']+1, app.config['WEB3'].eth.getTransactionCount(app.config['SENDER_ADDRESS']))
        nonce = app.config['NONCE']
        try:
            tx_hash = send_raw_transaction_no_wait(app.config['WEB3'], app.config['SENDER_ADDRESS'], app.config['SENDER_KEY'], recipient, amount, nonce, '')
        except Exception as e:
            return jsonify({{'status': 'error', 'message': f'Error sending transaction: {{e}}'}}), 500
    try:
        tx_receipt = wait_for_transaction_receipt(app.config['WEB3'], tx_hash)
        return jsonify({{'status': 'success', 'message':f'Funds successfully sent to {{recipient}} for amount {{amount}}.\\n{{tx_receipt}}'}}) , 200
    except Exception as e:
        return jsonify({{'status': 'error', 'message': f'Error sending transaction: {{e}}'}}), 500

if __name__ == '__main__':
    trial = 20
    while trial > 0:
        trial -= 1
        web3 = connect_to_geth('http://{eth_server_url}:{eth_server_http_port}', '{consensus}')
        if web3 == "":
            time.sleep(10)
        else:
            app.config['WEB3'] = web3
            break
        if trial == 0:
            sys.exit("Connection failed!")

    while web3.eth.blockNumber < 2:
        time.sleep(10)
    
    app.config['SENDER_ADDRESS'] = "{account_address}"
    app.config['SENDER_KEY'] = "{account_key}"
    app.config['NONCE'] = app.config['WEB3'].eth.getTransactionCount(app.config['SENDER_ADDRESS']) - 1
    app.run(host='0.0.0.0', port={port}, debug=True)

