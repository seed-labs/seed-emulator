# Funding Accounts

To send transactions, an account needs to have sufficient
fund. How do we fund accounts in the emulator? 
When we build the emulator, we create two types of 
accounts and assign balances to them. 
  - Accounts created for each Ethereum node
  - Independent accounts (called local accounts)   

These created accounts and their balances will be 
added to the genesis block. The genesis block is the initial
state of a blockchain, so a balance recorded in the genesis
block is the initial amount of fund available for the account. 

Sometimes accounts are generated during the run time. To
fund them, we have implemented a faucet service, which can
transfer part of its own fund to whoever requests for fund. 
Please see [this example](../../../examples/blockchain/D20_faucet)
for details. 


## Accounts Created for Ethereum Nodes

Each Ethereum node needs to have at least one account. 
The emulator will generate K accounts for each node based on
the user customization. These accounts will be generated using
a mnemonic phrase, and the generation is based on the BIP-44 specification. 
The default mnemonic phrase used in the emulator is the following:
```
great awesome fun seed security lab protect system network prevent attack future
```

Users can also replace it with a custom phrase. 
The following example shows how to get the default mnemonic phrase,
and how to change the account-generation parameters (the example does 
not change the phrase though). 

```
# Change the default account balance to 1000
mnemonic, _, _= blockchain.getEmuAccountParameters()
blockchain.setEmuAccountParameters(mnemonic=mnemonic, balance=1000, \
         total_per_node = total_accounts_per_node)
```

## Local Accounts Created by Emulator

The blockchain service will automatically create a number of accounts (with balance)
based on the default parameters, which can be reset using the `setLocalAccountParameters`
API. See the following (the mnemonic phrase used in the example is the same
as the default one). Users can recreate these accounts using the same set of 
parameters. 

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


## Add Local Accounts Created by Emulator

We can also add arbitrary accounts to the blockchain. In the following
example, the specified accounts will be given 999 Ethers. This account
balance will be included in the genesis block. 

```
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9', balance=999)
```

