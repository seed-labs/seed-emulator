# Chainlink User Service

The Chainlink User Service is an example to demonstrate how to
interact with the Chainlink service.

This example demonstrates how to interact with the Chainlink service using a
[user contract](./contracts/user_contract.sol). The user contract is deployed
by the Chainlink user server. This contract interacts with the Chainlink
service to get the latest price of an asset. The contract uses the LINK
token contract address and the oracle contract addresses to interact with the
Chainlink service. The user contract is funded with LINK tokens using the
faucet server. It sends a request to the Chainlink service to
get the latest price of an asset. The Chainlink service sends the response to
the user contract. The user contract then processes the response and displays
the latest price of the asset. Here is the flow:

1. Wait for the chainlink init server to be up. Get LINK token contract address and oracle contract addresses from the Chainlink init server
2. Create a web3 account and deploy the user contract
3. Fund the user account using the faucet server
4. Deploy the user contract
5. Invoke the user contract to set the LINK token contract address and
oracle contract addresses in the user contract
6. Send 1ETH to the LINK token contract to fund the user account with LINK tokens
7. Transfer LINK token to the user contract
8. Call the main function in the user contract


## Interact with the User contract deployed by the Chainlink User Service

The User contract can be found in the contracts folder: [user_contract.sol](./contracts/user_contract.sol)


### Checking the logs of the Chainlink User Service

The Chainlink User Service works as the flow described above. You can check
the logs of the Chainlink User Service to see the progress of the Chainlink
User Service. You can use the following command to check the logs of the
Chainlink User Service:

```bash
docker ps | grep Chainlink
```

Find the container ID of the Chainlink User Service, and
use it to check the logs of the Chainlink User Service:

```bash
docker logs <CONTAINER ID>
```

At the end of the logs, you will see the contract address of the user contract
deployed by the Chainlink User Service. And also you will see the latest ETH
price.  Here is the example output:

![Chainlink User Service Logs](./images/chainlink-user-service-logs.png)


### Interacting with the User contract using Remix

You can use the contract address to interact with the user contract using Remix
or any other Ethereum development tool as described below.


After the Chainlink User Service starts running, you can interact with the
[user contract](./contracts/user_contract.sol) deployed by the Chainlink User
Service. To get the User contract address, you can check the logs of the
Chainlink User Service. And another way is to do the following steps:

1. Execute the following command to get the container ID of the Chainlink User Service:
    ```bash
    docker ps | grep Chainlink-User
    ```
2. Execute the following command to get the bash shell of the Chainlink User Service:
    ```bash
    docker exec -it <CONTAINER ID> /bin/bash
    ```
3. After the Chainlink User Service deploys the user contract, you can find the
   contract address inside the container. You can use the following command to
   get the contract address:
    ```bash
    cat ./info/user_contract.json
    ```
4. Now you can interact with the user contract using Remix or other
   development tools. See [...]() 


### Interacting with the User contract using the Python script

You can also run the python script to interact with the user contract. The
python script can be found:
[test-chainlink-user-service.py](./test-chainlink-user-service.py). Using the
above steps, you can get the contract address which will be used in the python
script. You will need to change the `rpc_url`, `faucet_url` and
`user_contract_address` in the Python script according to the configuration.

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
