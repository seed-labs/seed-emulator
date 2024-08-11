#!/bin/env python3
# Create accounts from mnemonic code

from eth_account import Account
from web3 import Web3
import getopt, sys


def get_arguments(argv, options):
    # Remove 1st argument from the list of command line arguments
    argumentList = argv[1:]

    short_options = "n:"
    long_options = ""
    try:
      # Parsing argument
      arguments, values = getopt.getopt(argumentList, short_options, long_options)
      for arg, value in arguments:
         if arg in ("-n"):
             options['number'] = int(value)

    except getopt.error as err:
       print (str(err))


options = {'number': 5}  # default number of local accounts
get_arguments(sys.argv, options)
print("Usage: generate_accounts.py [-n number]")
print("%s local accounts will be created" % options['number'])


# This key derivation path is defined in the BIP-44 specification.
# The number 44 represents BIP-44; 60 represents Ethereum. 
# MetaMask uses this path to generate keys for Ethereum.
path_template = "m/44'/60'/0'/0/{}"  

# The words are from BIP-32 word list. We can pick the fist 11 words from
# the list and choose whatever order we want. However, we do not have much 
# control over the last word because it is partially decided by the checksum.
# NEVER NEVER use the accounts generated from this phrase in the Mainnet,
# because this phrase is public and everybody can get the private keys.
MNEMONIC_CODE = "great amazing fun seed lab protect network system " \
                "security prevent attack future"

Account.enable_unaudited_hdwallet_features()
for i in range(options['number']):
   acct = Account.from_mnemonic(MNEMONIC_CODE, 
                  account_path=path_template.format(i))

   print("Address:     " + acct.address)
   print("Private Key: " + acct.key.hex())
