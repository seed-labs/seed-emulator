#!/bin/env python3 
from flask import Flask, request, jsonify
import os
from web3 import Web3, HTTPProvider
import json


app = Flask(__name__)

ADDRESS_FILE_PATH = '/deployed_contracts/oracle_contract_address.txt'
HTML_FILE_PATH = '/var/www/html/index.html'

def get_sender_account_details():
    with open('./deployed_contracts/sender_account.txt', 'r') as account_file:
        lines = account_file.readlines()
        account_details = {{
        'address': lines[0].strip().split('Address: ')[1],
        'private_key': lines[1].strip().split('Private Key: ')[1]
        }}
    return account_details

@app.route('/display_contract_address', methods=['POST'])
def submit_address():
    address = request.json.get('contract_address')
    if not address:
        return jsonify({{'error': 'No address provided'}}), 400
    
    os.makedirs(os.path.dirname(ADDRESS_FILE_PATH), exist_ok=True)

    with open(ADDRESS_FILE_PATH, 'a') as file:
        file.write(address + '\\n')

    with open(HTML_FILE_PATH, 'a') as file:
        file.write(f'<h1>Oracle Contract Address: {{address}}</h1>\\n')

    return jsonify({{'message': 'Address saved and HTML updated successfully'}}), 200
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port={port})
