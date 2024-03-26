from typing import Dict

# Templates for configuration files remain the same
ChainlinkFileTemplate: Dict[str, str] = {}

ChainlinkFileTemplate['config'] = """\
[Log]
Level = 'info'

[WebServer]
AllowOrigins = '*'
SecureCookies = false

[WebServer.TLS]
HTTPSPort = 0

[[EVM]]
ChainID = '{chain_id}'

[[EVM.Nodes]]
Name = 'SEED Emulator'
WSURL = 'ws://{rpc_url}:{rpc_ws_port}'
HTTPURL = 'http://{rpc_url}:{rpc_port}'
"""

ChainlinkFileTemplate['secrets'] = """\
[Password]
Keystore = 'mysecretpassword'
[Database]
URL = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres?sslmode=disable'
"""

ChainlinkFileTemplate['api'] = """\
{username}
{password}
"""

ChainlinkFileTemplate['check_init_node'] = """\
URL="http://{init_node_url}"
EXPECTED_STATUS="200"
while true; do
    STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
    if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
        echo "Contracts deployed successfully!"
        break
    else
        echo "Waiting for the contracts to be deployed..."
        sleep 10
    fi
done
"""

ChainlinkFileTemplate['create_jobs'] = """\
DIRECTORY="/jobs/"
ORACLE_ADDRESS_FILE="/deployed_contracts/oracle_contract_address.txt"
TIMEOUT=1000
SLEEP_DURATION=10

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory $DIRECTORY does not exist."
    exit 1
fi

ELAPSED_TIME=0
while [ ! -f "$ORACLE_ADDRESS_FILE" ] && [ $ELAPSED_TIME -lt $TIMEOUT ]; do
    sleep $SLEEP_DURATION
    ELAPSED_TIME=$((ELAPSED_TIME + SLEEP_DURATION))
    echo "Waiting for Oracle address file..."
done

if [ ! -f "$ORACLE_ADDRESS_FILE" ]; then
    echo "Error: Oracle address file $ORACLE_ADDRESS_FILE does not exist after $TIMEOUT seconds."
    exit 1
fi

ORACLE_RELATION_RESPONSE=$(<"$ORACLE_ADDRESS_FILE")

if [ ! -d "$DIRECTORY" ]; then
        echo "Error: Directory does not exist."
        exit 1
    fi

    find "$DIRECTORY" -type f -name '*.toml' -print0 | while IFS= read -r -d $'\0' file; do
        sed -i "s/oracle_contract_address/$ORACLE_RELATION_RESPONSE/g" "$file"
        echo "Updated oracle contract address in $file"
    done

    echo "All TOML files have been updated."

chainlink admin login -f /api.txt

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory does not exist."
    exit 1
fi

for toml_file in "$DIRECTORY"*.toml; do
    if [ ! -f "$toml_file" ]; then
        echo "No TOML files found in the directory."
        continue
    fi

    echo "Creating Chainlink job from $toml_file..."
    chainlink jobs create "$toml_file"

    echo "Job created from $toml_file"
done

echo "All jobs have been created."
"""

ChainlinkFileTemplate['save_chainlink_address'] = """\
chainlink admin login -f /api.txt
ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')
if [ -z "$ETH_ADDRESS" ]; then
    echo "Error: Ethereum address not found."
    exit 1
fi
echo $ETH_ADDRESS > /deployed_contracts/sender.txt
"""

ChainlinkFileTemplate['set_authorized_sender'] = """\
#!/bin/env python3
import logging
import os
import json
import time
from web3 import Web3, HTTPProvider

rpc_url = "http://{rpc_url}:{rpc_port}"
private_key = "{private_key}"
contract_folder = './contracts/'
retry_delay = 60

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

web3 = Web3(HTTPProvider(rpc_url))
if not web3.isConnected():
    logging.error("Failed to connect to Ethereum node.")
    exit()

account = web3.eth.account.from_key(private_key)
gas_price = web3.eth.gasPrice

with open(os.path.join(contract_folder, 'oracle_contract.abi'), 'r') as abi_file:
    contract_abi = json.load(abi_file)

with open('./deployed_contracts/oracle_contract_address.txt', 'r') as file:
    oracle_contract_address = file.read().strip()
with open('./deployed_contracts/sender.txt', 'r') as file:
    sender = file.read().strip()

def authorize_address(sender, oracle_contract_address, nonce):
    try:
        oracle_contract = web3.eth.contract(address=oracle_contract_address, abi=contract_abi)
        txn_dict = oracle_contract.functions.setAuthorizedSenders([sender]).buildTransaction({{
            'chainId': {chain_id},
            'gas': 4000000,
            'gasPrice': web3.toWei('50', 'gwei'),
            'nonce': nonce,
        }})
        signed_txn = web3.eth.account.sign_transaction(txn_dict, account.privateKey)
        txn_receipt = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = web3.eth.wait_for_transaction_receipt(txn_receipt)
        logging.info(f'Success: {{txn_receipt}}')
        return True
    except Exception as e:
        logging.error(f'Error: {{e}}')
        if "replacement transaction underpriced" in str(e):
            logging.warning('Requeuing due to underpriced transaction')
            return False
        else:
            return True

authorization_success = False
while not authorization_success:
    nonce = web3.eth.getTransactionCount(account.address, 'pending')
    authorization_success = authorize_address(sender, oracle_contract_address, nonce)
    if not authorization_success:
        time.sleep(retry_delay)
"""

ChainlinkFileTemplate['nginx_site'] = """\
server {{
    listen {port};
    root /var/www/html;
    index index.html;
    server_name _;

    location / {{
        try_files $uri $uri/ @proxy_to_app;
    }}

    location @proxy_to_app {{
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

# ChainlinkFileTemplate['flask_app'] = """\
# import queue
# import threading
# from flask import Flask, request, jsonify
# from web3 import Web3, HTTPProvider
# import time
# import logging

# app = Flask(__name__)
# authorization_queue = queue.Queue()
# used_oracle_addresses = set()
# sender_to_oracle = {{}}
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# def load_unused_oracle_contract_address():
#     with open('./deployed_contracts/oracle_contract_address.txt', 'r') as file:
#         for line in file:
#             address = line.strip()
#             if address not in used_oracle_addresses:
#                 used_oracle_addresses.add(address)
#                 return address
#     return None

# def authorize_address(queue_item, nonce):
#     web3 = queue_item['web3']
#     account = queue_item['account']
#     sender = queue_item['sender']
#     oracle_contract_address = queue_item['oracle_contract_address']

#     if not oracle_contract_address:
#         logging.error({{'status': 'error', 'message': 'No Oracle contract address provided.'}})
#         return

#     try:
#         with open('./contracts/oracle_contract.abi', 'r') as abi_file:
#             contract_abi = abi_file.read()
#         oracle_contract = web3.eth.contract(address=oracle_contract_address, abi=contract_abi)

#         txn_dict = oracle_contract.functions.setAuthorizedSenders([sender]).buildTransaction({{
#             'chainId': {chain_id},
#             'gas': 4000000,
#             'gasPrice': web3.toWei('50', 'gwei'),
#             'nonce': nonce,
#         }})
#         signed_txn = web3.eth.account.sign_transaction(txn_dict, account.privateKey)
#         txn_receipt = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
#         txn_receipt = web3.eth.wait_for_transaction_receipt(txn_receipt)
#         logging.info({{'status': 'success', 'txn_receipt': str(txn_receipt), 'oracle_contract_address': oracle_contract_address, 'sender': sender}})
#     except Exception as e:
#         error_message = str(e)
#         logging.error({{'status': 'error', 'message': error_message, 'oracle_contract_address': oracle_contract_address, 'sender': sender}})        
#         if "replacement transaction underpriced" in error_message:
#             logging.info({{'status': 'retry', 'message': 'Requeuing due to underpriced transaction', 'sender': sender}})
#             authorization_queue.put(queue_item)

# def process_authorization_requests():
#     time.sleep(20)
#     while True:
#         queue_item = authorization_queue.get()
#         web3 = queue_item['web3']
#         account_address = queue_item['account'].address
#         nonce = web3.eth.getTransactionCount(account_address, 'pending')
#         authorize_address(queue_item, nonce)
#         authorization_queue.task_done()        

# threading.Thread(target=process_authorization_requests, daemon=True).start()

# @app.route('/setAuthorizedSender', methods=['POST'])
# def set_authorized_sender():
#     data = request.json
#     sender = data.get('sender')
    
#     if not sender:
#         return jsonify({{'status': 'error', 'message': 'Must provide sender address.'}}), 400
    
#     try:
#         web3 = Web3(Web3.HTTPProvider(f"http://{rpc_url}:{rpc_port}"))
#         private_key = "{private_key}"
#         account = web3.eth.account.from_key(private_key)
#         oracle_contract_address = load_unused_oracle_contract_address()
#         if not oracle_contract_address:
#             return jsonify({{'status': 'error', 'message': 'No unused Oracle contract addresses available.'}}), 400

#         sender_to_oracle[sender] = oracle_contract_address

#         authorization_queue.put({{
#             'web3': web3,
#             'account': account,
#             'sender': sender,
#             'oracle_contract_address': oracle_contract_address
#         }})

#         return jsonify({{
#             'status': 'success',
#             'message': 'Address authorization queued.',
#             'sender': sender,
#             'oracle_contract_address': oracle_contract_address
#         }})
#     except Exception as e:
#         return jsonify({{'status': 'error', 'message': str(e)}}), 500

# @app.route('/getSenderOracleRelation', methods=['GET'])
# def get_sender_oracle_relation():
#     sender = request.args.get('sender')
#     if not sender:
#         return jsonify({{'status': 'error', 'message': 'Must provide sender address.'}}), 400

#     oracle_contract_address = sender_to_oracle.get(sender)
#     if oracle_contract_address:
#         return jsonify({{'status': 'success', 'sender': sender, 'oracle_contract_address': oracle_contract_address}})
#     else:
#         return jsonify({{'status': 'error', 'message': 'Sender address not found.'}}), 404

# if __name__ == '__main__':
#     authorization_thread = threading.Thread(target=process_authorization_requests)
#     authorization_thread.daemon = True
#     authorization_thread.start()
#     app.run(debug=True, host='0.0.0.0', threaded=True)
# """



# ChainlinkFileTemplate['send_flask_request'] = """\
# URL="http://{init_node_url}"
# EXPECTED_STATUS="200"
# while true; do
#     STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
#     if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
#         echo "Contracts deployed successfully!"
#         break
#     else
#         echo "Waiting for the contracts to be deployed..."
#         sleep 10
#     fi
# done

# chainlink admin login -f /api.txt
# ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')
# AUTHORIZATION_RESPONSE=$(curl -s -X POST "http://{init_node_url}:{flask_server_port}/setAuthorizedSender" \\
#      -H "Content-Type: application/json" \\
#      -d "{{\\"sender\\": \\"$ETH_ADDRESS\\"}}" | jq -r '.status')

# if [ "$AUTHORIZATION_RESPONSE" = "success" ]; then
#     echo "Node address successfully authorized."
#     ORACLE_RELATION_RESPONSE=$(curl -s "http://{init_node_url}:{flask_server_port}/getSenderOracleRelation?sender=$ETH_ADDRESS" | jq -r '.oracle_contract_address')
#     DIRECTORY="/jobs/"

#     if [ ! -d "$DIRECTORY" ]; then
#         echo "Error: Directory does not exist."
#         exit 1
#     fi

#     find "$DIRECTORY" -type f -name '*.toml' -print0 | while IFS= read -r -d $'\0' file; do
#         sed -i "s/oracle_contract_address/$ORACLE_RELATION_RESPONSE/g" "$file"
#         echo "Updated oracle contract address in $file"
#     done

#     echo "All TOML files have been updated."
# else
#     echo "Failed to authorize node address."
# fi
# """

ChainlinkFileTemplate['send_get_eth_request'] = """\
chainlink admin login -f /api.txt
ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')
curl -s -X POST http://{faucet_server_url}:{faucet_server_port}/getEth \\
     -H "Content-Type: application/json" \\
     -d "{{\\"chainlinkNodeAddress\\": \\"$ETH_ADDRESS\\"}}" > /dev/null 2>&1 &
echo "Get Ethereum request sent to faucet server."
"""