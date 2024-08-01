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

- `ChainlinkServer`: Operates the Chainlink software starting with a
  pre-configured setup. It funds a Chainlink node and an Ethereum account using
  faucet, deploys an oracle contract with the LINK token contract address and
  node address as an authorized user, and establishes a one-to-one relationship
  between the node and the contract. Pre-configured jobs are created with the
  oracle contract address on the server.

- `ChainlinkUserServer`: To demonstrate how to use the Chainlink service. 




<a id="interact-with-cli"></a>
## Interact with Chainlink using CLI

You can interact with the Chainlink nodes using the Chainlink CLI. 
The Chainlink CLI is a command-line tool that allows you to interact with
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
## Chainlink User Server 

The Chainlink User Server is an example to demonstrate how to
use the Chainlink service to request external data.
To do that, a [user contract](./contracts/user_contract.sol) needs to
be deployed to the blockchain. Users will interact with this 
contract, which will interact with the Chainlink service to get 
the data from the outside. 


### Set up the user contract 

Setting up the user contract takes several steps. When the user node
start, these steps will be automatically carried out. 

1. Get LINK token contract address and oracle contract addresses
   from the Ethereum Utility server
2. Create an Ethereum account and fund the account using the faucet server
3. Deploy the user contract
4. Invoke the `setLinkToken` function of the user contract to 
   set the LINK token contract address
5. Invoke the `addOracles` function of the user contract to add
   oracle contract addresses in the user contract
6. Send 1 ETH to the LINK token contract to fund the user account with LINK tokens
7. Invoke the `transfer` function of the LINK contract to transfer 100 LINK tokens
   from the user account to the user contract account.


### How the process works

Once everything is set up, a user can request ETH price by invoking 
the `requestETHPriceData(api, path)` function in the user contract. 
This will trigger a series of actions: 

- Upon receiving a request, the user contract invokes the LINK contract,
  which invokes the Chainlink oracle contracts. The involvement of
  the LINK contract ensures that the oracle gets paid (with LINK tokens) 
  - Each oracle gets `x` number of LINK tokens for each job
  - The LINK contract will deduct `k*x` number of LINK tokens from the 
    user contract account (`k` is the number of oracles invoked)

- Each oracle contract emits a message to notify its outside counterpart, 
  i.e., a Chainlink node, which is always monitoring the blockchain
  for such messages

- Each Chainlink node does the following:
   - Fetch the outside data from the specified `api`
   - Process the data it using the specified `path` 
   - Give the result to the oracle contract, which invokes
     the callback function provided by the user contract

- The user contract processes and save the response; for example, it may
  calculate the average from the data sent back from all the oracles
- The user eventually uses a local call to get the response  


### Check the logs of the Chainlink user server

You can check the logs on the Chainlink User Server to 
see the entire progress.

```bash
# Find the container ID of the Chainlink User Service
$ docker ps | grep Chainlink-User

$ docker logs -f <container ID>
```

In the logs, you will see the contract address of the user contract
deployed by the Chainlink User Service. 
At the end of the logs, you will see the latest ETH price. 

```
...
INFO - Successfully set Link token contract address in user contract.
INFO - Successfully add oracles to user contract.
INFO - Sent 1 ETH to LINK token contract successfully.
INFO - Transferred LINK tokens to user contract successfully.
INFO - User contract balance: 100000000000000000000
INFO - Requested ETH price data successfully.
INFO - Awaiting responses... Current responses count: 0
INFO - Awaiting responses... Current responses count: 0
INFO - Awaiting responses... Current responses count: 3
INFO - Response count: 3
INFO - Average ETH price: 381753
INFO - Chainlink user example service completed.
```


### Interact with the user contract using Remix

You can interact the user contract using Remix
or other Ethereum development tool.
To get the User contract address, you can check the logs of the
Chainlink User Server or use the following method

```bash
# Get the container ID 
$ docker ps | grep Chainlink-User

# Get the user contract address from the Chainlink-User container
$ docker exec -it <container ID> cat /chainlink_user/info/user_contract.json
{"contract_address": "0x313bF07a4Ba9275AfEaB59c19c922a0e027e9c89"}
```

With this address, you can invoke the `requestETHPriceData(api, path)` function
of the user contract. The `api` is the external API where we want to get the
data from, and the `path` is the json path that leads to the specific 
data item in the response (the response from the external API contains 
a lot of data items; if we replace `PRICE` with `OPENDAY`, we can select
a different item):

```
api = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD"
path = "RAW,ETH,USD,PRICE"
```

### Interact with the user contract using Python

You can also use a python program to interact with the user contract. 
A sample program `test_user.py` can be found in the current folder.
We need to change the IP addresses and the user contract address 
in the program, as they are emulator specific. The ethereum nodes
have "Ethereum" included in their container names, while the 
faucet server has "Faucet" included in the names. 

```python
eth_url    = "http://10.160.0.72:8545"      # one of the ethereum nodes
faucet_url = "http://10.163.0.72:80/fundme" # the faucet server
user_contract_address = "0x313bF07a4Ba9275AfEaB59c19c922a0e027e9c89"
```

The script will interact with the user contract and display the latest price of
the asset. Here is the output:

```
2024-06-05 09:24:48,048 - INFO - Sending a fund request to the Faucet server
2024-06-05 09:25:05,119 - INFO - Successfully requested funds from faucet: { ... }
INFO - Checking current ETH price in user contract
INFO - Current ETH price in user contract: 381384
INFO - Initiating a new request for ETH price data
INFO - API for ETH price: https://min-api.cryptocompare.com/data/pricemultifull?fsyms=ETH&tsyms=USD
INFO - Path for extracting price: RAW,ETH,USD,PRICE
INFO - Sent transaction for ETH price data request. 
       Hash: 0xc28ae96432d8214e99070ee65ec7a0076c9599f6b9b75df273eb57cfc5d5334c
INFO - Status of Transaction receipt for ETH price data request: 1
INFO - Request for ETH price data successful
INFO - Sleeping for 60 seconds to allow oracles to respond
INFO - Checking ETH price
INFO - Responses received from oracles
INFO - Responses count: 3
INFO - Updated ETH price: 381405
```
