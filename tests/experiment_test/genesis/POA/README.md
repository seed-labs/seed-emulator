# GenesisTestCase

## Overview
The `GenesisTestCase.py` script performs a unit test for deploying smart contract using the genesis block.

## Test Cases
The script includes the following test cases:
1. `test_poa_chain_connection`: This test verifies if the blockchain is up and running by attempting to connect to the PoA chain multiple times within a specified timeout.
2. `test_deployed_contract`: This test checks if the custom erc20 token is deployed succesfully on the blockchain.

## How to Run
To execute the test script, simply run the following command in your terminal:
```bash
./GenesisTeseCase.py
```
Upon completion, a `test_log` folder will be created, which contains detailed logs of the test results. The logs are also printed to the terminal.
