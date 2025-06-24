
LIGHTHOUSE_BN_CMD = """lighthouse --debug-level info bn --datadir /tmp/bn/local-testnet/testnet --testnet-dir /tmp/bn/local-testnet/testnet --enable-private-discovery --staking --enr-address {ip_address}  --enr-udp-port 9000 --enr-tcp-port 9000 --port 9000 --http-address {ip_address} --http-port 8000 --http-allow-origin "*" --disable-packet-filter --target-peers {target_peers} --execution-endpoint http://localhost:8551 --execution-jwt /tmp/jwt.hex --subscribe-all-subnets {bootnodes_flag} &"""

LIGHTHOUSE_VC_CMD = """lighthouse --debug-level info vc --datadir /tmp/vc/local-testnet/testnet --testnet-dir /tmp/vc/local-testnet/testnet --init-slashing-protection --beacon-nodes http://{ip_address}:8000 --suggested-fee-recipient {acct_address} --http --http-address 0.0.0.0 --http-allow-origin "*" --unencrypted-http-transport &"""

LIGHTHOUSE_WALLET_CREATE_CMD = """lighthouse account_manager wallet create --testnet-dir /tmp/vc/local-testnet/testnet --datadir /tmp/vc/local-testnet/testnet --name "seed" --password-file /tmp/seed.pass"""

LIGHTHOUSE_VALIDATOR_CREATE_CMD = """lighthouse --testnet-dir /tmp/vc/local-testnet/testnet --datadir /tmp/vc/local-testnet/testnet account validator create --wallet-name seed --wallet-password /tmp/seed.pass --count 1"""


VALIDATOR_DEPOSIT_PY = """\
from web3 import Web3
from eth_account import Account
import json
import glob
import os


# Connect to Ethereum node (execution layer)
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Load keystore JSON file
with open('/root/.ethereum/keystore/{keystore_filename}') as f:
    keystore = json.load(f)

# Provide the password used when the account was created
password = "admin"

# Decrypt to get the private key
private_key = Account.decrypt(keystore, password)
acct = Account.from_key(private_key)

# Should now print: 0xd4cc43e3f2830f9082495dba904b57fc2ca95cbd
print(f"[deposit.py] Decrypted account: {{acct.address}}")

balance = w3.eth.get_balance(acct.address)
print(f"[deposit.py] Account balance: {{w3.from_wei(balance, 'ether')}} ETH")

# Deposit contract address in local devnet (same as mainnet for standard Lighthouse config)
deposit_contract_address = '0x00000000219ab540356cBB839Cbe05303d7705Fa'


# Base directory for validator folders
val_base_dir = '/tmp/vc/local-testnet/testnet/validators'

# Find all paths matching 0x*/eth1-deposit-data.rlp
rlp_files = glob.glob(os.path.join(val_base_dir, '0x*/eth1-deposit-data.rlp'))

if not rlp_files:
    raise FileNotFoundError("[deposit.py] No eth1-deposit-data.rlp files found in validator directories.")

# Use the first match (or loop over them if you want to deposit for multiple validators)
rlp_path = rlp_files[0]
print(f"[deposit.py] Using deposit data file: {{rlp_path}}")

# Read RLP deposit data
with open(rlp_path, 'r') as f:
    rlp_data = f.read().strip()

# Construct transaction
tx = {{
    'to': deposit_contract_address,
    'from': acct.address,
    'data': rlp_data,
    'value': w3.to_wei(32, 'ether'),
    'gas': 200000,
    'gasPrice': w3.to_wei('1', 'gwei'),  # adjust as needed
    'nonce': w3.eth.get_transaction_count(acct.address),
    'chainId': 1337,
}}

print("[deposit.py] Making deposit transaction")
# Sign and send
signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"[deposit.py] Deposit tx sent! Tx hash: {{w3.to_hex(tx_hash)}}")
"""

