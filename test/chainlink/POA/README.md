# Unit Test for Ethereum PoA Blockchain with Chainlink Node

## Overview

The `ChainlinkPOATestCase.py` performs a unit test for Ethereum PoA blockchain with chainlink node using [unittest](https://docs.python.org/3/library/unittest.html) library. In this script, it consists of 4 testcases: (1) `test_chainlink_node_health`, (2) `test_chainlink_init_node_health`, (3) `test_link_token_deployment`, (4) `test_oracle_contract_deployment`

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

In this test script, it comprises 8 test cases: (1) `test_chainlink_node_health`, (2) `test_chainlink_init_node_health`, (3) `test_link_token_deployment`, (4) `test_oracle_contract_deployment`.

- Testcase (1) `test_chainlink_node_health` test the health of a normal chainlink node
- Testcase (2) `test_chainlink_init_node_health` test the health of a initalizer chainlink node
- Testcase (3) `test_link_token_deployment` test if link token is deployed. And also checks of the balance of the link token is assigned to the owner.
- Testcase (4) `test_oracle_contract_deployment` test if oracle contract is deployed. And also checks if the oracle contract is assigned to the owner and the link token is assigned to the oracle contract.