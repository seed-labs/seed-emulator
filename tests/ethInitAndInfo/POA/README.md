# EthInitAndInfoTestCase

## Overview
The `EthInitAndInfoTestCase.py` script performs a unit test for deploying smart contract using the EthInitAndInfo Server. The script connects to the PoA chain, deploys a contract, and verifies the contract deployment and configuration. It also tests the connection to the EthInitAndInfo server and the contract registration API.

## Test Cases
The script includes the following test cases:
1. `test_poa_chain_connection`: This test verifies if the blockchain is up and running by attempting to connect to the PoA chain multiple times within a specified timeout.
2. `test_init_info_server_connection`: This test checks the connection to the EthInitAndInfo server by sending a request to the server and verifying the response status.
3. `test_contract_info`: This test verifies the deployment of the contract using the contract_info API. It fetches contract information from the server and checks if the expected contract details are returned.
4. `test_deployed_contract`: This test ensures that a contract is deployed on the blockchain, can receive funds, and is correctly configured. It involves creating a test account, funding it, and checking the contract deployment and balance.
5. `test_api_call`: This test registers a contract using the register_contract API and verifies the registration by fetching the contract information.

## How to Run
To execute the test script, simply run the following command in your terminal:
```bash
./EthInitAndInfoTestCase.py
```
Upon completion, a `test_log` folder will be created, which contains detailed logs of the test results. The logs are also printed to the terminal.
