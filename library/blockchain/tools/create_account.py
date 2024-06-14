#!/bin/env python3

import sys
from eth_account import Account

##############################################
KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{}"
MNEMONIC = "great amazing fun seed lab protect network system " \
           "security prevent attack future"
##############################################

if len(sys.argv) < 2:
    total = 10
else: 
    total = int(sys.argv[1])

Account.enable_unaudited_hdwallet_features()

for i in range(total):
    path = KEY_DERIVATION_PATH.format(i)
    account = Account.from_mnemonic(MNEMONIC, account_path=path)
    address = account.address
    key     = account.privateKey.hex()
    print("address: {}".format(address))
    print("key:     {}".format(key))

