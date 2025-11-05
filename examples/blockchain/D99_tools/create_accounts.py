#!/bin/env python3

from eth_account import Account
import json, sys

def generate_keys_from_mnemonic_eth_account(mnemonic: str, num_accounts: int = 5) -> list:
    """
    Generate Ethereum keys from mnemonic using eth-account
    
    Args:
        mnemonic: BIP-39 mnemonic phrase
        num_accounts: Number of accounts to generate
    
    Returns:
        List of dictionaries containing account information
    """
    Account.enable_unaudited_hdwallet_features()
    
    accounts = []
    for i in range(num_accounts):
        # Derive account using standard BIP-44 path: m/44'/60'/0'/0/{index}
        account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
        
        accounts.append({
            'account_index': i,
            'address': account.address,
            'private_key': account.key.hex(),
        })
    
    return accounts

# Example usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        total = 10
    else:
        total = int(sys.argv[1])

    mnemonic = "gentle always fun glass foster produce north tail security list example gain"
    accounts = generate_keys_from_mnemonic_eth_account(mnemonic, total)
    

    for account in accounts:
        print(f"Account {account['account_index']}:")
        print(f"  Address: {account['address']}")
        print(f"  Private Key: {account['private_key']}")
        print("-" * 50)

    print("*** Saved account data to prefunded_accounts.json")
    with open("prefunded_accounts.json", "w") as f:
        json.dump(accounts, f, indent=4) # indent for pretty-printing

