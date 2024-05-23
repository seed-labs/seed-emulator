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
URL="http://{init_node_url}:{init_node_port}/contracts_info?name={contract_name}"
EXPECTED_STATUS="200"
while true; do
    STATUS=$(curl -Is "$URL" | head -n 1 | awk '{{print $2}}')
    
    if [ "$STATUS" == "$EXPECTED_STATUS" ]; then
        echo "Link Token contract deployed successfully on the init node!"
        break
    else
        echo "Waiting for the link token contract to be deployed..."
        sleep 10
    fi
done
"""

ChainlinkFileTemplate['create_jobs'] = """\
DIRECTORY="/chainlink/jobs/"
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

chainlink admin login -f /chainlink/password.txt

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
URL="http://{init_node_url}:{init_node_port}"
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

RESPONSE=$(curl -X POST http://{init_node_url}:{init_node_port}/register_contract \\
     -H "Content-Type: application/json" \\
     -d "{{\\"contract_name\\":\\"oracle-{contract_name}\\", \\"contract_address\\":\\"$(tail -n 1 /deployed_contracts/oracle_contract_address.txt)\\"}}")

echo "$RESPONSE"
"""

ChainlinkFileTemplate['send_get_eth_request'] = """\
# Wait for the Chainlink node to be up
while true; do
    sleep 20
    # Get Ethereum address
    chainlink admin login -f /chainlink/password.txt
    ETH_ADDRESS=$(chainlink keys eth list | grep 'Address:' | awk '{{print $2}}')

    # Check if the address is empty
    if [ -z "$ETH_ADDRESS" ]; then
        echo "Error: Ethereum address cannot be empty."
    else
        # Address is not empty, break the loop
        echo "Ethereum address: $ETH_ADDRESS"
        break
    fi
done
FAUCET_SERVER_URL={faucet_server_url}
FAUCET_SERVER_PORT={faucet_server_port}
RPC_URL="http://{rpc_url}:{rpc_port}"
AMOUNT=5
TIME_LIMIT=100

check_balance() {{
    response=$(curl -s -X POST $RPC_URL -H "Content-Type: application/json" --data '{{"jsonrpc":"2.0","method":"eth_getBalance","params":["'$1'", "latest"],"id":1}}')
    balance_hex=$(echo $response | jq -r '.result')
    if [ $balance_hex == "null" ]; then
        echo 0
    else
        echo $((16#${{balance_hex#0x}}))
    fi
}}

SERVER_STATUS=0

echo "Waiting for the faucet server to be up..."

while [ "$SERVER_STATUS" -ne 200 ]; do
    SERVER_STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/)
    if [ "$SERVER_STATUS" -ne 200 ]; then
        echo "Faucet server not up yet. Retrying..."
        sleep 5
    fi
done

echo "Faucet server is up. Proceeding to send fund request."
echo "curl -X POST -d address=$ETH_ADDRESS&amount=$AMOUNT http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/fundme > /dev/null 2>&1 &"
curl -X POST -d "address=$ETH_ADDRESS&amount=$AMOUNT" "http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/fundme" > /dev/null 2>&1 &
echo "Fund request sent to the faucet server."

start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    
    balance=$(check_balance $ETH_ADDRESS)
    balance_eth=$(echo $balance | awk '{{printf "%.18f\\n", $1 / 1000000000000000000}}')
    
    echo "Current balance: $balance_eth ETH"
    
    funded=$(echo $balance_eth | awk '{{print ($1 > 0) ? "1" : "0"}}')
    
    if [ $funded -eq 1 ]; then
        echo "Funds already received. Exiting..."
        break
    elif [ $elapsed_time -gt $TIME_LIMIT ]; then
        echo "Account not funded after $TIME_LIMIT seconds. Sending another request..."
        echo "curl -X POST -d address=$ETH_ADDRESS&amount=$AMOUNT http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/fundme > /dev/null 2>&1 &"
        curl -X POST -d "address=$ETH_ADDRESS&amount=$AMOUNT" "http://$FAUCET_SERVER_URL:$FAUCET_SERVER_PORT/fundme" > /dev/null 2>&1 &
        start_time=$(date +%s)
    else
        echo "Account not yet funded. Waiting..."
    fi
    sleep 30
done

mkdir -p /deployed_contracts
echo $ETH_ADDRESS > /deployed_contracts/auth_sender.txt
"""