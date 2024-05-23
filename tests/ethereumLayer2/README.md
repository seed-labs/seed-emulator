# Unit Test for Ethereum Layer2 Blockchain

## Overview

The `EthereumLayer2TestCase.py` performs a unit test for Ethereum layer2 blockchain using [unittest](https://docs.python.org/3/library/unittest.html) library.

In this script, it consists of 10 test cases:

1. test_l1_node_connection
2. test_sc_deployment
3. test_seq_node_connection
4. test_seq_node_status
5. test_ns_node_synchronization
6. test_chain_id
7. test_deposit
8. test_tx_execution
9. test_batch_submission
10. test_state_submission

## How to run

This unit testing have a loader to load all the Ethereum layer2 service unit testing cases.

```sh
# Run the Test Script
./EthereumLayer2TestCase.py
```

Once the test is done, `test_log` folder including the test result is created.
A test result is not only printed out to the terminal also saved as a file named `log.txt`. The logs can be used when investigating the failure cases.

```sh
$ tree test_log
test_log
├── build_log
├── compile_log
├── containers_log
└── log.txt
```

## Test Case Explained

1. `test_l1_node_connection`: Test http connection with geth in layer1 (ethereum) node.
2. `test_sc_deployment`: Test if layer2 smart contract deployment is completed.
3. `test_seq_node_connection`: Test http connection with op-geth in layer2 sequencer node.
4. `test_seq_node_status`: Test if layer2 sequencer is building blocks.
5. `test_ns_node_synchronization`: Test if the blockchain state of non-sequencer nodes are synced.
6. `test_chain_id`: Test if layer2 chain id is set correctly.
7. `test_deposit`: Test depositing ETH from layer1 to layer2.
8. `test_tx_execution`: Test if a layer2 tx is executed.
9. `test_batch_submission`: Test if layer2 txs are batched and submitted to layer1.
10. `test_state_submission`: Test if layer2 states are submitted to layer1.
