# Unit Test for Ethereum PoW Blockchain

## Overview

The `EthereumPOWTestCase.py` performs a unit test for Ethereum PoW blockchain using [unittest](https://docs.python.org/3/library/unittest.html) library. In this script, it consists of 4 testcases: (1) `test_pow_chain_connection`, (2) `test_pow_chain_id`, (3) `test_pow_chain_consensus`, (4) `test_import_account`, (5) `test_pow_emulator_account`, (6) `test_pow_create_account`, (7) `test_pow_send_transaction`, and (8) `test_pow_peer_counts`.

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./EthereumPOWTestCase.py
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

In this test script, it comprises 8 test cases: (1) `test_pow_chain_connection`, (2) `test_pow_chain_id`, (3) `test_pow_chain_consensus`, (4) `test_import_account`, (5) `test_pow_emulator_account`, (6) `test_pow_create_account`, (7) `test_pow_send_transaction`, and (8) `test_pow_peer_counts`.

Testcase (1) `test_pow_chain_connection` test http connection with geth.
Testcase (2) `test_pow_chain_id` test a chain id.
Testcase (3) `test_pow_chain_consensus` test if a chain consensus is POA.
Testcase (4) `test_import_account` test if importing account works.
Testcase (5) `test_pow_emulator_account` test if emulator accounts are created with an expected amount of balance.
Testcase (6) `test_pow_create_account` test if creating new account works.
Testcase (7) `test_pow_send_transaction` test if a sending transaction works.
Testcase (8) `test_pow_peer_counts` test if peer counts of a geth node.