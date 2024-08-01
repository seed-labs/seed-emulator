# EthUtilityServer

The Utility server has two roles. The first role is to help deploy smart contract,
and the second role is to provide contract addresses to others. In Ethereum, once a
contract has been deployed, it will be assigned an address. Users need to
know this address to interact with the contract. The Utility server 
hosts a web server for others to register contract addresses. 

- [Create a Utility server](#create-utility-server)
- [Deploy a contract](#deploy-contract)
- [Interact with the Uility server](#interact-with-server)

<a id="create-utility-server"></a>
## Create Utility Server

We first need to add a Utility server to a blockchain.
This example uses a pre-built block component (`D00_ethereum_poa`), 
which already has a Utility server.
In the [D00_ethereum_poa](../D00_ethereum_poa/) example, these lines are
used to create a utility server


```python
util_server:EthUtilityServer = blockchain.createEthUtilityServer(
           vnode='utility',
           port=5000,
           linked_eth_node='eth6',
           linked_faucet_node='faucet')
```

We can specify the following parameters:
- `vnode`: the virtual node name of the Utility server.
- `port`: a port number, used by the server to set up a web server.
- `linked_eth_node`: the faucet server needs to link to an eth node, so it can
  sends out transactions to the blockchain. We just need to provide the name
  of an existing eth node, but we need to make sure that the eth node
  has enabled the http connection (otherwise, it cannot accept external requests).
- `linked_faucet_node`: the Utility server will create an Ethereum account, which
  is used to deploy contracts. The Utility server will use the faucet server
  to find the account. 

Because this server is already created in the base component,
we just need to get an instance of this object:

```python
eth        = emu.getLayer('EthereumService')
blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
name       = blockchain.getUtilityServerNames()[0]
utility    = blockchain.getUtilityServerByName(name)
```


<a id="deploy-contract"></a>
## Deploy a contract

To deploy a contract using the Utility server, 
we need to set `abi` and `bin` file. A path can be both relative and absolute.

```python
utility.deployContractByFilePath(contract_name='test',
                        abi_path="./Contracts/contract.abi",
                        bin_path="./Contracts/contract.bin")
```

It should be noted that the contract deployment will happen after the emulator
starts, so this API will set up the contract deployment on the Utility server. 


<a id="interact-with-server"></a>
## Interact with the Utility server using `curl`

After the emulator starts, we can interact with the Utility server
using the `curl` command. To do that, 
we first need to get the server's IP address (the 
port number used in the example is `5000`). 

```sh
$ docker ps | grep -i utility
e22e918b4c90   output_hnode_150_host_0  ...  as162h-UtilityServer-10.150.0.71
```

In this example, the url of the server is `http://10.150.0.71:5000/`. 


### Register a contract

To register a contract with the Utility server, we use a POST request
to send the contract information (JSON format) 
to the server's `/register_contract` API. 
See the following example: 

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"contract_name": "test999", "contract_address": "0xc0ffee254729296a45a3885639AC7E10F9d54979"}' \
  http://10.150.0.71:5000/register_contract
```

### Get a list of registered contracts

We can use the following API to get a list of all the registered contracts. 

```sh
curl http://10.150.0.71:5000/all
curl http://10.150.0.71:5000/contracts_info
```


### Get a contract address by its name

If we just want to get the address of a particular contract, we can provide
the `name` argument. 

```sh
curl http://10.150.0.71:5000/contracts_info?name=test
```


## Interact with the Utility server using Python

We can write Python programs to interact with the Utility server.
A helper class 
called [UtilityServerHelper.py](../../../library/blockchain/UtilityServerHelper.py) 
is created to make writing such programs easier. 
