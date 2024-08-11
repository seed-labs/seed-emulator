#!/bin/env python3

from flask import Flask, request, jsonify
import os
from web3 import Web3, HTTPProvider
import json


app = Flask(__name__)

PORT       = {port}
DIR_PREFIX = "{dir_prefix}"

ADDRESS_FILE_DIRECTORY = DIR_PREFIX + '/deployed_contracts'
ADDRESS_FILE_PATH  = DIR_PREFIX + '/deployed_contracts/contract_address.txt'
HTML_FILE_PATH     = '/var/www/html/index.html'

@app.route('/')
def index():
    return 'OK', 200
    
@app.route('/register_contract', methods=['POST'])
def register_contract():
    name = request.json.get('contract_name')
    address = request.json.get('contract_address')
    if not name:
        return jsonify({{'error': 'No contract name provided'}}), 400
    if not address:
        return jsonify({{'error': 'No contract address provided'}}), 400

    if not os.path.exists(ADDRESS_FILE_DIRECTORY):
        os.makedirs(ADDRESS_FILE_DIRECTORY)
        with open(ADDRESS_FILE_PATH, 'w') as address_file:
            contract_info = {{
                name: address
            }}
            json.dump(contract_info, address_file, indent=4)
        return jsonify(contract_info), 200
        
    else:
        with open(ADDRESS_FILE_PATH, 'r') as address_file:
            contract_info = json.load(address_file)
        contract_info[name] = address
        with open(ADDRESS_FILE_PATH, 'w') as address_file:
            json.dump(contract_info, address_file, indent=4)
        return jsonify(contract_info), 200
        
    
@app.route('/all', methods=['GET'])
@app.route('/contracts_info', methods=['GET'])
def get_contract_info():
    contract_name = request.args.get('name')

    if not os.path.exists(ADDRESS_FILE_DIRECTORY):
        return jsonify({{'error': 'The named contract does not exist'}}), 400

    else:
        with open(ADDRESS_FILE_PATH, 'r') as address_file:
            contract_info = json.load(address_file)
        if not contract_name:
            return jsonify(contract_info), 200
        else:
            if contract_name in contract_info.keys():
                return jsonify(contract_info[contract_name]), 200
            else:
                return jsonify({{'error': 'No contract address matching with a given contract name'}}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT)

