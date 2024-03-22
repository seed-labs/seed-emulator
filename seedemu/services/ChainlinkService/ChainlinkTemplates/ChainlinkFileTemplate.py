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
ChainID = '1337'

[[EVM.Nodes]]
Name = 'SEED Emulator'
WSURL = 'ws://{ip_address}:8546'
HTTPURL = 'http://{ip_address}:8545'
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

ChainlinkFileTemplate['get_oracle_contract_address'] = """\
URL="http://{init_node_url}"

ORACLE_CONTRACT=$(curl -s "$URL" | grep -oP 'Oracle Contract: \K[0-9a-zA-Z]+' | head -n 1)
DIRECTORY="/jobs/"

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory does not exist."
    exit 1
fi

find "$DIRECTORY" -type f -name '*.toml' -print0 | while IFS= read -r -d $'\0' file; do
    sed -i "s/oracle_contract_address/$ORACLE_CONTRACT/g" "$file"
    echo "Updated oracle contract address in $file"
done

echo "All TOML files have been updated."
"""

ChainlinkFileTemplate['create_jobs'] = """\
chainlink admin login -f /api.txt
DIRECTORY="/jobs/"

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

ChainlinkFileTemplate['get_keystore_content'] = """\
import subprocess
import os

file_path = '/tmp/eth_key'
output_file_name = 'eth_keystore.json'
output_dir = '/tmp'
output_path = os.path.join(output_dir, output_file_name)

os.makedirs(output_dir, exist_ok=True)

with open(file_path, 'r') as file:
    lines = file.readlines()

address = ''

for line in lines:
    if 'Address:' in line:
        # If found, split the line by ':' and strip any whitespace or newlines
        address = line.split(':')[1].strip()
        break

if address:
    command = f'chainlink keys eth export {{address}} -p /tmp/pass --output {{output_path}}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f'Keystore content saved successfully in {output_path}')
    else:
        print('Error executing command:', result.stderr)
else:
    print('Address not found in the file.')
"""

ChainlinkFileTemplate['get_native_token_faucet'] = """\
from web3 import Web3
from eth_account import Account
import json

provider_url = '{rpc_url}'  # Replace with your Ethereum node provider URL
keystore_path = '/tmp/eth_keystore.json'
passcode_path = '/tmp/pass'
abi_path = '/tmp/faucet_contract_abi'  # Path to the file containing the ABI
contract_path = '/tmp/faucet_contract'  # Path to the file containing the contract address

w3 = Web3(Web3.HTTPProvider(provider_url))

with open(passcode_path, 'r') as file:
    passphrase = file.read().strip()
with open(keystore_path) as keyfile:
    encrypted_key = keyfile.read()
    private_key = Account.decrypt(json.loads(encrypted_key), passphrase)
    account = Account.from_key(private_key)

with open(contract_path, 'r') as file:
    contract_address = file.read().strip()

with open(abi_path) as abi_file:
    contract_abi = json.load(abi_file)

contract = w3.eth.contract(address=contract_address, abi=contract_abi)

nonce = w3.eth.getTransactionCount(account.address)
txn = contract.functions.getEth().buildTransaction({
    'chainId': w3.eth.chain_id,
    'gas': 2000000,
    'gasPrice': w3.toWei('50', 'gwei'),
    'nonce': nonce,
})

signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)

txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

print(f'Transaction hash: {txn_hash.hex()}')
"""