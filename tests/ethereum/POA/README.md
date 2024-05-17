# Unit Test for Ethereum PoA Blockchain

## Overview

The `EthereumPOATestCase.py` performs a unit test for Ethereum PoA blockchain using [unittest](https://docs.python.org/3/library/unittest.html) library. In this script, it consists of 4 testcases: (1) `test_poa_chain_connection`, (2) `test_poa_chain_id`, (3) `test_poa_send_transaction`, (4) `test_poa_chain_consensus`, (5) `test_poa_peer_counts`, (6) `test_poa_emulator_account`, (7) `test_poa_create_accounts`, and (8) `test_import_account`.

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./EthereumPOATestCase.py
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

In this test script, it comprises 8 test cases: (1) `test_poa_chain_connection`, (2) `test_poa_chain_id`, (3) `test_poa_send_transaction`, (4) `test_poa_chain_consensus`, (5) `test_poa_peer_counts`, (6) `test_poa_emulator_account`, (7) `test_poa_create_accounts`, and (8) `test_import_account`.

Testcase (1) `test_poa_chain_connection` test http connection with geth.
Testcase (2) `test_poa_chain_id` test a chain id.
Testcase (3) `test_poa_send_transaction` test if a sending transaction works.
Testcase (4) `test_poa_chain_consensus` test if a chain consensus is POA.
Testcase (5) `test_poa_peer_counts` test if peer counts of a geth node.
Testcase (6) `test_poa_emulator_account` test if emulator accounts are created with an expected amount of balance.
Testcase (7) `test_poa_create_accounts` test if creating new account works.
Testcase (8) `test_import_account` test if importing account works.
