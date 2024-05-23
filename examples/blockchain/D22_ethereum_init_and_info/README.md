# EthInitAndInfo Server

EthInitAndInfo Server has two roles. First role to deploy a contract when all the containers are up. A contract abi and bin files are given at build time. And the second role of the server to provide contract address. In Ethereum, once a contract is deployed, every contract will be assigned an address. Users need to know the address to interact with the contract. The EthInitAndInfo Server will host a web server for user to register a contract with a tuple of `contract_name` and `contract_address`. Then, user can get the list of contract information or a contract address corresponded with the given contract name.

- [Create an EthInitAndInfo server](#add-ethinitandinfo-server)
- [Deploy a contract](#deploy-contract)
- [Interact with EthInitAndInfo server](#interact-with-server)

<a id="add-ethinitandinfo-server"></a>
## Create EthInitAndInfo Server

We first need to add an EthInitAndInfo Server to a blockchain using the `createEthInitAndInfoServer` method. After creating the server, we need to set `linkedEthNode` and `linkedFaucetNode` to connect to the eth node via web3 and send fund api to the faucet node.
```python
# Create the EthInit server, and set port number of the server, the eth node and faucet server.
ethInitInfo:EthInitAndInfoServer = blockchain.createEthInitAndInfoServer(vnode='eth_init_info', 
                                                                             port=5000, 
                                                                             linked_eth_node=random.choice(eth_nodes),
                                                                             linked_faucet_node=random.choice(faucet_info))
```

<a id="deploy-contract"></a>
## Deploy a contract

To deploy a contract using `EthInitAndInfo` server, we need to set `abi` and `bin` file. A path can be both relative and absolute.
```python
ethInitInfo.deployContract(contract_name='test', 
                        abi_path="./Contracts/contract.abi",
                        bin_path="./Contracts/contract.bin")
```

<a id="interact-with-server"></a>
## Interact with a EthInitAndInfo server

### Get ip addr of the eth-init-info node. 
```sh
$ docker ps | grep -i init
e22e918b4c90   output_hnode_150_host_0                                     "/start.sh"      2 minutes ago   Up 2 minutes                                                 as162h-EthInitAndInfo-10.150.0.71
```
In this example, the url of the server is `http://10.150.0.71:5000/`. Please replace it according to your setup.

### Register a contract

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"contract_name": "test999", "contract_address": "0xc0ffee254729296a45a3885639AC7E10F9d54979"}' \
  http://10.150.0.71:5000/register_contract
```

- This curl command sends a POST request to `http://10.150.0.71:5000/register_contract` to register a contract.
- The request body is in JSON format and contains the keys `contract_name` and `contract_address`.
- Replace `"test999"` with the actual contract name and `"0xc0ffee254729296a45a3885639AC7E10F9d54979"` with the actual contract address you want to register.

### Get a list of contract_name:contract_address pairs

```sh
curl http://10.150.0.71:5000/contracts_info
```

- This curl command sends a GET request to `http://10.150.0.71:5000/contracts_info` to retrieve a list of contract_name:contract_address pairs.
- It does not require any parameters in the URL.

### Get a contract address by its name

```sh
curl http://10.150.0.71:5000/contracts_info?name=test
```

- This curl command sends a GET request to `http://10.150.0.71:5000/contracts_info` with a query parameter `name=test` to retrieve the contract address corresponding to the given contract name ("test" in this example).
- Replace `"test"` with the actual contract name for which you want to retrieve the contract address.

These commands demonstrate how to register a contract, retrieve a list of registered contracts, and retrieve a specific contract's address by its name using HTTP requests.
