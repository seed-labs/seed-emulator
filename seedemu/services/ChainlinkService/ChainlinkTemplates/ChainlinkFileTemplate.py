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

ChainlinkFileTemplate['save_sender_address'] = """\
chainlink admin login -f /api.txt
ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')
if [ -z "$ETH_ADDRESS" ]; then
    echo "Error: Ethereum address not found."
    exit 1
fi
mkdir -p /deployed_contracts
echo $ETH_ADDRESS > /deployed_contracts/sender.txt
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

ChainlinkFileTemplate['flask_app'] = """\
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
"""

ChainlinkFileTemplate['send_flask_request'] = """\
URL="http://{init_node_url}"
EXPECTED_STATUS="200"

while true; do
    STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
    if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
        echo "Server is up!"
        break 
    else
        echo "Retrying in 10 seconds.."
        sleep 10 
    fi
done

RESPONSE=$(curl -X POST http://{init_node_url}:{flask_server_port}/display_contract_address \\
     -H "Content-Type: application/json" \\
     -d "{{\\"contract_address\\":\\"$(tail -n 1 /deployed_contracts/oracle_contract_address.txt)\\"}}")

echo "$RESPONSE"
"""

ChainlinkFileTemplate['send_get_eth_request'] = """\
sleep 30
chainlink admin login -f /api.txt
ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')
FAUCET_SERVER_URL={faucet_server_url}
FAUCET_SERVER_PORT={faucet_server_port}

echo "Sending fund request..."

curl -s -X POST http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/getEth \\
     -H "Content-Type: application/json" \\
     -d "{{\\"chainlinkNodeAddress\\": \\"$ETH_ADDRESS\\"}}" > /dev/null 2>&1 &
     
echo "Get Ethereum request sent to faucet server."
"""