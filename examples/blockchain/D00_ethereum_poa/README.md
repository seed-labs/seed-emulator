# Ethereum Blockchain (POA)


## Create a blockchain

To create a blockchain, we first create the `EthereumService`, and then
create a blockchain inside this service. The service supports
multiple chains.  

```
eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)
```

## Create pre-funded accounts (add to the genesis block)

Each Ethereum node will have at least one accounts on it, and more
can be created. The system use a set of default values to create
and configure these accounts. Users can replace these default
values with their own values. 

```python
mnemonic, _, _= blockchain.getEmuAccountParameters()
blockchain.setEmuAccountParameters(mnemonic=mnemonic, balance=1000, \
        total_per_node = total_accounts_per_node)
```

Users can also add arbitrary pre-funded account to the blockchain.

```
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=30)
```

All the accounts created during the build time will be added (along with their
balance) to the genesis block. Therefore, their balances are recognized. 

For detailed account management instructions, see
[this manual](../../../docs/user_manual/blockchain/accounts.md)



## Create Ethereum nodes




## Other useful APIs

These APIs are not used in this example, but they might be useful
to satisfy additional emulation needs.


- Set custom `geth` command option: for commonly-used options, we already
  have APIs to set them. However, for options not covered by these APIs,
  users can use this generic API to set them. 
  ```
  eth_node.setCustomGethCommandOption("--http --http.addr 0.0.0.0")
  ```

- Use custom `geth` binary file: some users want to run a modified version
  of the `geth` software on a particular node. They can do this
  using the following API.
  ```
  eth_node.setCustomGeth("./custom_geth_binary")
  ```


## Supported platforms 

As of 12/12/2023, SEED Emulation Ethereum layer supports AMD platforms and
partially supports ARM platforms.
Please see details below.

| Ethereum Consensus | AMD | ARM |
| ------------------ | --- | --- |
| PoW                |  O  |  X  |
| PoA                |  O  |  O  |
| PoS                |  O  |  O  |

