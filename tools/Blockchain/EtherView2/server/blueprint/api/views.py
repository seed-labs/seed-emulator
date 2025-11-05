from web3 import Web3
from flask import jsonify, Blueprint, current_app
from eth_account import Account
from .transaction.views import tx
from .etherscan.views import etherscan

api = Blueprint('api', __name__, url_prefix='/api')
api.register_blueprint(tx)
api.register_blueprint(etherscan)


@api.route('/data')
def api_data():
    return jsonify({"message": "Hello from Flask API!", "status": "success"})


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
        account = Account.from_mnemonic(current_app.configure['mnemonic_phrase'],
                                        account_path=current_app.configure['key_derivation_path'].format(index))
        accounts.append({"address": account.address,
                         "name": local_account_names[index],
                         "type": "local"})

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
