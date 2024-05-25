# Create Pre-funded Accounts

When we build the emulator, we can create two types of 
accounts: (1) accounts managed by each Ethereum node,
and (2) independent accounts (called local accounts).   
These created accounts and their balances will be added to the genesis block,
so the balances are recognized by the blockchain. 


## Accounts on Ethereum Nodes

The emulator uses a default mnemonic phrase to generate the accounts 
on each Ethereum nodes. The generation is based on the
BIP-44 specification. The phrase is the following:
```
great awesome fun seed security lab protect system network prevent attack future
```
Users can also replace it with a custom phrase. 
The following example shows how to get the default mnemonic phrase,
and how to change the account-generation parameters (the example does 
not change the phrase). 

```
# Change the default account balance to 1000
mnemonic, _, _= blockchain.getEmuAccountParameters()
blockchain.setEmuAccountParameters(mnemonic=mnemonic, balance=1000, \
         total_per_node = total_accounts_per_node)
```


## Local Accounts 

The blockchain service will automatically create a number of accounts (with balance)
based on the default parameters, which can be reset using the `setLocalAccountParameters`
API. See the following (the mnemonic phrase used in the example is the same
as the default one). 

```
words = "great amazing fun seed lab protect network system security prevent attack future"
blockchain.setLocalAccountParameters(mnemonic=words, total=10, balance=100)
```

This will generate 10 accounts, each with a balance of 100 Ethers.
You can use [this program](./code/generate_accounts.py) to generate
the same set of accounts (this program uses the same 
mnemonic phrase). 

```
$ generate_accounts.py -n 10
Usage: generate_accounts.py [-n number]
8 local accounts will be created
Address:     0xA2a2...154c
Private Key: 0x6510...c3cfe5a8a54bddeba90d667
...
```

It should be noted that the key derivation is based on the 
BIP-44 specification. The path is `"m/44'/60'/0'/0/{}"`, 
where 44 represents BIP-44 and 60 represents Ethereum.
MetaMask also uses this path to generate keys for Ethereum.
Therefore, if we provide the same mnemonic phrase
to MetaMask, it will generate the same set of keys. 


