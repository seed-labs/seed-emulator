from web3 import Web3
from eth_account import Account
import json

# Enable Web3 auto-import features
w3 = Web3()

Account.enable_unaudited_hdwallet_features()

mnemonic = "gentle always fun glass foster produce north tail security list example gain"

derivation_path = "m/44'/60'/0'/0/3"

wallet = w3.eth.account.from_mnemonic(mnemonic, account_path=derivation_path)

private_key = wallet.privateKey.hex()
address = wallet.address

password = "admin"

keystore = Account.encrypt(private_key, password)

keystore_json = json.dumps(keystore, indent=4)

print("Address:", address)
print("Private Key:", private_key)
print("Keystore JSON:", keystore_json)
