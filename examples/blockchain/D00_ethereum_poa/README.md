# Ethereum Blockchain (POA)

## Create a blockchain

To create a blockchain, we first create the `EthereumService`, and then
create a blockchain inside this service. The service supports
multiple chains.  

```python
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

```python
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=30)
```

All the accounts created during the build time will be added (along with their
balance) to the genesis block. Therefore, their balances are recognized. 

For detailed account management instructions, see
[this manual](../../../docs/user_manual/blockchain/accounts.md)


## Create Ethereum Nodes

To create an Ethereum node, we just need to provide a node name (virtual node),
and use the following API. 

```python
e = blockchain.createNode('node0')
```

Each node can be configured and customized using the provided APIs. See the
[`EthereumServer`](../../../seedemu/services/EthereumService/EthereumServer.py)
class for the supported APIs.



## Other useful APIs

These APIs are not used in this example, but they might be useful
to satisfy additional emulation needs.

- Set custom `geth` command option: for commonly-used options, we already
  have APIs to set them. However, for options not covered by these APIs,
  users can use this generic API to set them. 
  ```python
  eth_node.setCustomGethCommandOption("--http --http.addr 0.0.0.0")
  ```

- Use custom `geth` binary file: some users want to run a modified version
  of the `geth` software on a particular node. They can do this
  using the following API.
  ```python
  eth_node.setCustomGeth("./custom_geth_binary")
  ```


## Create Faucet and Information Servers

In this example, we also create a faucet server and a utility server.
These two servers are not used in this example, but they are used 
by other examples. Because many applications require these 
two servers, they are two essential elements in the SEED 
blockchain emulator. 

These two servers are not used in this example. The faucet 
server is used in the example [D20_faucet](../D20_faucet/), while the 
utility server is used in the example
[D21_deploy_contract](../D21_deploy_contract) to help deploy
smart contracts. 


## Binding to Physical Nodes

All the virtual nodes need to be bound to physical nodes. We have
implemented an API called `getAllServerNames` to make it easy to 
get all the server names, including the ethereum nodes, the faucet
nodes, and the init-and-info servers. 

```python
for _, servers in blockchain.getAllServerNames().items():
    for server in servers:
       emu.addBinding(Binding(server))
```

In our example, we did not set any filter in the binding, so the binding
will be random, i.e., each virtual node will be randomly bound to
a physical node. 


## Supported platforms 

As of 5/25/2024, SEED Emulation Ethereum layer supports AMD platforms and
partially supports ARM platforms. Please see details below.

| Ethereum Consensus | AMD | ARM |
| ------------------ | --- | --- |
| PoW                |  O  |  X  |
| PoA                |  O  |  O  |
| PoS                |  O  |  O  |

