from web3 import Web3
from flask import jsonify, Blueprint, current_app, request
from eth_account import Account
from hexbytes import HexBytes
from .transaction.views import tx
from .etherscan.views import etherscan

api = Blueprint('api', __name__, url_prefix='/api')
api.register_blueprint(tx)
api.register_blueprint(etherscan)


@api.route('/restore_accounts')
def generate_keys_from_mnemonic_eth_account():
    mnemonic, num_accounts = request.args.get('mnemonic', ""), int(request.args.get('accountNum', 5))
    Account.enable_unaudited_hdwallet_features()

    accounts = []
    for i in range(num_accounts):
        account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")

        accounts.append({
            'account_index': i,
            'address': account.address,
            'private_key': account.key.hex(),
            'name': f"ETH-ACCOUNT-{i}"
        })

    return jsonify({'data': accounts, 'status': True})


@api.route('/get_accounts')
def get_accounts():
    accounts = []

    # Get the accounts from the emulator
    for address in current_app.eth_accounts:
        item = current_app.eth_accounts[address]
        accounts.append({"address": address,
                         "name": item["name"],
                         "type": "emulator"})

    # Generate local accounts using the mnemonic phrase.
    Account.enable_unaudited_hdwallet_features()
    local_account_names = current_app.configure['local_account_names']
    for index in range(len(local_account_names)):
        account = Account.from_mnemonic(
            current_app.configure['mnemonic_phrase'],
            account_path=current_app.configure['key_derivation_path'].format(index)
        )
        accounts.append({
            "address": account.address,
            # "privateKey": f"0x{HexBytes(account.privateKey).hex()}",
            "name": local_account_names[index],
            "type": "local"
        })

    return accounts


@api.route('/get_web3_providers')
def get_web3_providers():
    providers = []
    for key in current_app.eth_nodes:
        node = current_app.eth_nodes[key]
        providers.append("http://%s:8545" % node['ip'])

    return providers


@api.route('/get_web3_url')
def get_web3_url():
    return jsonify({"data": current_app.web3_url, "status": True})


@api.route('/get_web3_total_eth')
def get_web3_total_eth():
    total_wei = 0
    accounts = get_accounts()

    w3 = Web3(Web3.HTTPProvider(current_app.web3_url))
    if not w3.isConnected():
        return str(total_wei)

    for acct in accounts:
        total_wei += w3.eth.get_balance(acct['address'])
    total_eth = w3.fromWei(total_wei, 'ether')
    return f'{total_eth:.8f}'


@api.route('/sendTX', methods=['POST'])
def send_eth_transaction():
    ret = {'status': False}
    from_address = request.form.get('sender')
    from_key = request.form.get('senderKey')
    to_address = request.form.get('receiver')
    amount_eth = float(request.form.get('amount', 0))
    nonce = int(request.form.get('nonce', 0))
    nonce = nonce if nonce > 0 else None
    if not all([from_address, to_address, from_key]):
        ret['message'] = "params error"
        current_app.logger.error(ret['message'])
        return jsonify(ret)

    """Send ETH transaction from one account to another"""
    w3 = Web3(Web3.HTTPProvider(current_app.web3_url))
    if not w3.isConnected():
        ret['message'] = f"Web3 connect failed: {current_app.web3_url}"
        current_app.logger.error(ret['message'])
        return jsonify(ret)

    try:
        # Convert amount to wei
        amount_wei = w3.toWei(amount_eth, 'ether')
        # Get current gas price
        gas_price = w3.eth.gas_price
        # Standard ETH transfer gas limit
        gas_limit = 21000
        # Calculate total cost (amount + gas fees)
        total_cost = amount_wei + (gas_limit * gas_price)
        # Build transaction
        transaction = {
            'to': to_address,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce if nonce is not None else w3.eth.get_transaction_count(from_address),
            'chainId': 1337
        }

        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, from_key)
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        ret.update({
            'data': tx_hash.hex(),
            'status': True
        })
    except Exception as e:
        ret['message'] = f"Error sending transaction (ignored): {e}"
        current_app.logger.error(ret['message'])
    return jsonify(ret)
