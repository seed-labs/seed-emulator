# Unit Test for Ethereum PoA Blockchain with Chainlink Node

## Overview

The `ChainlinkPOATestCase.py` performs a unit test for Ethereum PoA blockchain with chainlink node using [unittest](https://docs.python.org/3/library/unittest.html) library. In this test script, it comprises 7 test cases: (1) `test_poa_chain_connection`, (2) `test_chainlink_init_node_health`, (3) `test_chainlink_node_health`, (4) `test_link_token_deployment`, (5) `test_oracle_contract_deployment`, (6) `test_chainlink_node_balance`, (7) `test_user_contract`

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./ChainlinkPOATestCase.py
```

Once the test is done, `test_log` folder including the test result is created.
A test result is not only printed out to the terminal also saved as a file named `log.txt`. The logs can be used when investigating the failure cases.

```
$ tree test_log
test_log
├── build_log
├── compile_log
├── containers_log
└── log.txt
```


## Test Case Explain

- Testcase (1) `test_poa_chain_connection` test the connection of the PoA chain
- Testcase (2) `test_chainlink_init_node_health` test the health of a initalizer chainlink node (checks the address of link token and oracle contract on the init web server)
- Testcase (3) `test_chainlink_node_health` test the health of a normal chainlink node and also checks the oracle contract - chainlink node connection
- Testcase (4) `test_link_token_deployment` test if link token is deployed. And also checks the total supply of the link token.
- Testcase (5) `test_oracle_contract_deployment` test if oracle contract is deployed. Also checks if getChainlinkToken returns the expected LINK token address and verify the expected Chainlink Ethereum address against the authorized sender
- Testcase (6) `test_chainlink_node_balance` test if the chainlink node is funded or not
- Testcase (7) `test_user_contract` test the chainlink service by deploying a user contract