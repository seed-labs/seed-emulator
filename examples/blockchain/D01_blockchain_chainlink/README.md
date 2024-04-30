# Chainlink Example
This example demonstrates how to use Chainlink with a blockchain. The developer manual can be found [here](../../../docs/developer_manual/06-chainlink-service.md)

## Table of Contents
- [Chainlink Example](#chainlink-example)
  - [Table of Contents](#table-of-contents)
  - [Building the Emulation](#building-the-emulation)
  - [To Do](#to-do)

## Building the Emulation
1. Build the components for hybrid-internet:
    ```bash
    python3 hybrid-internet.py
    ```
    This will generate the `hybrid-internet.bin` file.
    - Information about the hybrid-internet example can be found here: [hybrid-interet](../../C00-hybrid-internet/README.md)
2. Using the `hybrid-internet.bin` file, build the blockchain and faucet components:
    ```python
    python3 blockchain-poa.py
    ```
    This is a modified version of the blockchain-poa example. The only difference is that the websocket is enabled on all nodes for the Chainlink service to listen. And a faucet is initialized to fund the Chainlink service with ETH tokens. This will generate the `blockchain-poa.bin` file.
    - Information about the blockchain-poa example can be found here: [blockchain-poa](../D00-blockchain-poa/README.md)
    - Information about the ethereum-faucet example can be found here: [faucet](../../B12-ethereum-faucet/blockchain.py)
3. Now that the blockchain and faucet components are built, initialize the Chainlink service:
    ```python
    python3 chainlink-service.py
    ```
    This will generate the `chainlink-service.bin` file. This file will also generate the docker-compose file for the Chainlink service in the `/output` directory.
    - Information about the Chainlink service can be found here: [chainlink-service](./chainlink-service.md)
4. There is an automated user example service also built to showcase how the user can interact with the Chainlink service. This example service is built using the Chainlink service and the blockchain service. To build the example service, run the following command:
    ```python
    python3 chainlink-user-service.py
    ```
    This file will also generate the docker-compose file for the Chainlink example service in the `/output` directory.
    - Information about the Chainlink example service can be found here: [chainlink-example-service](./chainlink-user-service.md)

## To Do
- [ ] Make a video tutorial for the Chainlink example and how to interact with the Chainlink service