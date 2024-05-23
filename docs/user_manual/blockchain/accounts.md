# Create Pre-funded Accounts

Three types of accounts:
- Accounts managed by each Ethereum node
- Independent accounts (called local accounts)  

These accounts and their balances will be added to the genesis block.
Therefore, the balances are recognized by the blockchain. 


## Accounts on Ethereum Nodes

Example 

```
# Change the default account balance to 1000
mnemonic, _, _= blockchain.getEmuAccountParameters()
blockchain.setEmuAccountParameters(mnemonic=mnemonic, balance=1000, \
         total_per_node = total_accounts_per_node)

default: total is 1, balance is 32,
phrase is
great awesome fun seed security lab protect system network prevent attack future
```


## Local Accounts 


```
words = "great amazing fun seed lab protect network system security prevent attack future"
blockchain.setLocalAccountParameters(mnemonic=words, total=10, balance=100)

Default: total is 5, balance is 10, the phrase is the same as the example
```


## Various Account APIs

Import accounts, etc. 


## Generating Accounts Using Python

Tools to generate accounts (put in the `code/` folder) 

