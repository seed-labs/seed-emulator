# Chainlink Service 

Chainlink is a decentralized oracle network designed to securely connect smart
contracts on blockchain platforms with external data and services. It acts as a
bridge between blockchains and real-world data, such as financial market
prices, weather information, and other off-chain data sources. By providing
reliable data feeds to smart contracts, Chainlink enhances the functionality
and applicability of blockchain applications across various industries,
enabling them to execute transactions based on real-time information.

The Chainlink service in the emulator consists of two types of nodes (called
servers in the emulator):

- `ChainlinkInitializerServer`: Deploys the LINK token contract essential for
  building the Chainlink decentralized oracle network and hosts a web server
  displaying the LINK token and oracle contract addresses.

- `ChainlinkServer`: Operates the Chainlink software starting with a
  pre-configured setup. It funds a Chainlink node and a Web3 account using
  faucet, deploys an oracle contract with the LINK token contract address and
  node address as an authorized user, and establishes a one-to-one relationship
  between the node and the contract. Pre-configured jobs are created with the
  oracle contract address on the server.


- [Add Chainlink service](#add-chainlink-service)
- [The Initializer Server](#init-server)
- [Interact with Chainlink using CLI](#interact-with-cli)
- [Interact with Chainlink using GUI](#interact-with-gui)
- [Chainlink user service](#user-service)


<a id="add-chainlink-service"></a>
## Add the Chainlink Service

Detailed explanation of each of the code is already provided as comments
in the code, so we will not repeat them in this document. 
Each server (Chainlink node) is protected by a login page; the default username 
is `seed@seed.com` and the default password is `Seed@emulator123`. 
We can change them using the following API of the server 
class (the username must be an email address and the password
must have 16 to 50 characters).

```python
setUsernameAndPassword(username = '<username>', password = '<password>')
```

<a id="init-server"></a>
## The Initializer Server

To deploy the Chainlink service on a blockchain, we need to deploy contracts
and conduct fund-transfer transactions on the blockchain. These transactions
have to be done during the run time, not the build time. 
We create a special node called Chainlink Initializer server to serve these
purposes. On this server, we also run a web server, which provides
the addresses for various contracts, including the LINK token contract
and the oracle contracts deployed by Chainlink nodes. 
This web server can be accessed via `http://<host_ip>`. 
After the emulator starts running, the web server will display
the oracle contract address and the LINK token contract address. 
This information is useful for Chainlink services.

```
$ docker ps | grep Chainlink-Init
e0763604de80  as170h-Chainlink-Init-10.170.0.72

$  curl 10.170.0.72:8080/contracts_info
{
  "link_token_contract": "0x7C71A6d36e5F89Db2c62872346BF733714c8E434",
  "oracle-chainlink_node_0": "0xacCd860e5Ff9BaFd809c902FA6F1b27F317dD72e",
  "oracle-chainlink_node_1": "0x601d53D7D99655909d54a7c0135612A383247078",
  "oracle-chainlink_node_2": "0x5d76c2B6B12C106CDb83fbEAC54A3853fBC1A9DF"
}
```


<a id="interact-with-cli"></a>
## Interact with Chainlink using CLI

Chainlink CLI: You can interact with the Chainlink nodes using the Chainlink
CLI. The Chainlink CLI is a command-line tool that allows you to interact with
the Chainlink node. You can use the CLI to create and manage Chainlink jobs,
check the status of the Chainlink node, and more. The Chainlink CLI can be
accessed by running the following command on Chainlink nodes: 

```bash
# chainlink admin login

Default username: seed@example.com
Default password: blockchainemulator
```

Instructions on how to use the Chainlink CLI can be found
[here](https://github.com/smartcontractkit/chainlink/wiki/Command-Line-Options).


<a id="interact-with-gui"></a>
## Interacting with Chainlink using GUI

### Login  

Each Chainlink node comes with a web UI that can
be used to interact with the node.  You can access the UI by navigating
to `http://<host_ip>:6688`. It allows you to create and manage Chainlink jobs. 

  ```
  Default username: seed@seed.com
  Default password: Seed@emulator123
  ```

### Dashboard

After the login, we will enter the dashboard. From here, 
we can create and manage Chainlink jobs,
check the status of the Chainlink node, and more.
It will show the address of 
the account created during chainlink start command which 
should be funded with 5 ETH tokens.
```
Account Balance
Address  0xC485bC418643777f98A0C0eF31244Ea766028088
Native Token Balance 5.000000000000000000
LINK Balance         0.00000000
```

Instructions on how to use the dashboard to manage jobs can be
found [here](https://docs.chain.link/chainlink-nodes)



<a id="user-service"></a>
## Chainlink User Service 

The Chainlink User Service is an example to demonstrate how to
use the Chainlink service to request Ethereum price from 
a real-world server. 

To do that, a [user contract](./contracts/user_contract.sol) needs to
be deployed to the blockchain. This contract interacts with the Chainlink
service to get the latest price of an asset. 
It uses the LINK token contract address and the oracle contract addresses
to interact with the Chainlink service. 
The user contract is funded with LINK tokens using the
faucet server. It sends a request to the Chainlink service to
get the latest price of an asset. The Chainlink service gets the
response from the outside, and sends the response to
the user contract. The user contract then processes the response and displays
the latest price of the asset. The entire flow is described in
the following. 

1. Wait for the chainlink init server to be up. 
Get LINK token contract address and oracle contract addresses from the Chainlink init server
2. Create a web3 account and deploy the user contract
3. Fund the user account using the faucet server
4. Deploy the user contract
5. Invoke the user contract to set the LINK token contract address and
oracle contract addresses in the user contract
6. Send 1ETH to the LINK token contract to fund the user account with LINK tokens
7. Transfer LINK token to the user contract
8. Call the main function in the user contract


### Checking the logs of the Chainlink User Service

You can check the logs of the Chainlink User Service to
see the progress of the Chainlink User Service.
You can use the following command to do this.

```bash
# Find the container ID of the Chainlink User Service
$ docker ps | grep Chainlink-User

$ docker logs <container ID>
```

In the logs, you will see the contract address of the user contract
deployed by the Chainlink User Service. 
At the end of the logs, you will see the latest ETH price. 

```
INFO - <Response [200]>
INFO - Account funded: 0xb57EedE06Ef66be651b2CC95F87d9F5617b43f57
INFO - User contract deployed at address: 0x7D34979B3D53c29f870180a8F426A4c843b0cF40
Success: Funds successfully sent to 0xb57EedE06Ef66be651b2CC95F87d9F5617b43f57 for amount 10.
... 
INFO - Sent 1 ETH to LINK token contract successfully.
INFO - Transferred LINK tokens to user contract successfully.
INFO - User contract balance: 100000000000000000000
INFO - Requested ETH price data successfully.
INFO - Awaiting responses... Current responses count: 0
INFO - Awaiting responses... Current responses count: 0
INFO - Awaiting responses... Current responses count: 3
INFO - Response count: 3
INFO - Average ETH price: 302127
INFO - Chainlink user example service completed.
```

### Interacting with the User contract using Remix

You can use the contract address to interact with the user contract using Remix
or other Ethereum development tool.
After the Chainlink User Service starts running, you can interact with the
[user contract](./contracts/user_contract.sol) deployed by the Chainlink User
Service. To get the User contract address, you can check the logs of the
Chainlink User Service. Here is another way is to get the address:

```bash
# Get the container ID 
$ docker ps | grep Chainlink-User

# Display "./info/user_contract.json" from the Chainlink-User container
$ docker exec -it <container ID> cat ./info/user_contract.json
{"contract_address": "0x7D34979B3D53c29f870180a8F426A4c843b0cF40"}
```

With this address, you can interact with the contract using Remix or other
development tools. 


### Interacting with the User contract using Python

You can also use a python program to interact with the user contract. The
python script can be found here:
[test-chainlink-user-service.py](./test-chainlink-user-service.py). 
Using the above steps, we can get the contract address, which needs to
be assigned to the `user_contract_address` parameter in the Python script.
We also need to change the `rpc_url` and `faucet_url` 
parameters based on the actual IP addresses in the emulator. 
The following gives an example. 

```python
self.rpc_url = "http://10.160.0.72:8545"
self.faucet_url = "http://10.160.0.74/fundme"
self.user_contract_address = "0x7D34979B3D53c29f870180a8F426A4c843b0cF40"
```

The script will interact with the user contract and display the latest price of
the asset. Here is the example output:

```bash
2024-04-25 11:45:58,043 - INFO - Checking current ETH price in user contract
2024-04-25 11:45:58,049 - INFO - Current ETH price in user contract: 315075
2024-04-25 11:45:58,049 - INFO - Initiating a new request for ETH price data
2024-04-25 11:45:58,049 - INFO - API for ETH price: https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD
2024-04-25 11:45:58,049 - INFO - Path for extracting price: RAW,ETH,USD,PRICE
2024-04-25 11:45:58,062 - INFO - Sent transaction for ETH price data request. Hash: 0x8cabcb43db6a39805e51c065248342d7804dbd8705928732eb7aa20ef21effc7
2024-04-25 11:46:13,042 - INFO - Status of Transaction receipt for ETH price data request: 1
2024-04-25 11:46:13,042 - INFO - Request for ETH price data successful
2024-04-25 11:46:13,042 - INFO - Sleeping for 60 seconds to allow oracles to respond
2024-04-25 11:47:13,124 - INFO - Checking ETH price
2024-04-25 11:47:13,131 - INFO - Responses received from oracles
2024-04-25 11:47:13,141 - INFO - Responses count: 2
2024-04-25 11:47:13,141 - INFO - Updated ETH price: 314862
```
