# Unit Test for Ethereum PoS Blockchain

## Overview

The `EthereumPOSTestCase.py` performs a unit test for Ethereum PoS blockchain using [unittest](https://docs.python.org/3/library/unittest.html) library. In this script, it consists of 4 testcases: (1) `test_pos_geth_connection`, (2) `test_pos_contract_deployment`, (3) `test_pos_chain_merged`, and (4) `test_pos_send_transaction`.

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./EthereumPOSTestCase.py
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

#### Expected Result

```sh
$ ./blockchain-pos-test.py
test_pos_geth_connection (__main__.POSTestCase) ...
==========Trial 1==========
Connection failed

==========Trial 2==========
Connection failed

==========Trial 3==========
Connection Succeed:  http://10.151.0.72:8545
Connection Succeed:  http://10.152.0.72:8545
Connection Succeed:  http://10.153.0.72:8545
ok
test_pos_contract_deployment (__main__.POSTestCase) ...
========================================
Waiting for contract deployment...
current blockNumber :  1
Total in txpool: 0 (http://10.151.0.72:8545)
Total in txpool: 0 (http://10.152.0.72:8545)
Total in txpool: 0 (http://10.153.0.72:8545)

--- (omitted) ---

========================================
Waiting for contract deployment...
current blockNumber :  8
Total in txpool: 1 (http://10.151.0.72:8545)
Total in txpool: 1 (http://10.152.0.72:8545)
Total in txpool: 1 (http://10.153.0.72:8545)
++++Deposit Succeed++++
Deposit contract address: "0xa1ad48288461ee030a2f391128d055faef5263c9"
Submitting deposit for validator 0...
Submitting deposit for validator 1...
Submitting deposit for validator 2...
Submitting deposit for validator 3...
Submitting deposit for validator 4...
Submitting deposit for validator 5...
Submitting deposit for validator 6...
Submitting deposit for validator 7...
Submitting deposit for validator 8...
Submitting deposit for validator 9...
Submitting deposit for validator 10...
Submitting deposit for validator 11...
Submitting deposit for validator 12...
Submitting deposit for validator 13...
Submitting deposit for validator 14...
Submitting deposit for validator 15...

ok
test_pos_chain_merged (__main__.POSTestCase) ...
========================================
Terminal total difficulty is set to 30.
The blockNumber will not increase from 15, if the merge is failed.
So we will assume that the blockNumber is over 17, the merge is succeed.
========================================
current blockNumber :  8
current blockNumber :  9
current blockNumber :  11
current blockNumber :  12
current blockNumber :  13
current blockNumber :  15
current blockNumber :  17
current blockNumber :  18
ok
test_pos_send_transaction (__main__.POSTestCase) ... {
  "nonce": 0,
  "from": "0xF5D434D36dD2bF53d2D1dB4FD40076A0C1C44F8d",
  "to": "0x513C434dBA61AE5CFEf4552daC2D2f85450870aA",
  "value": 100000000000000000,
  "chainId": 1337,
  "gas": 30000,
  "maxFeePerGas": 3000000000,
  "maxPriorityFeePerGas": 2000000000,
  "data": ""
}
Transaction Hash: 0x47af1280d3fb576cbe44954c40b691d95a0c2d2b2faa0c09231d2553befaee21
Waiting for receipt ...
Abbreviated transaction ----
{
   "from": "0xF5D434D36dD2bF53d2D1dB4FD40076A0C1C44F8d",
   "to": "0x513C434dBA61AE5CFEf4552daC2D2f85450870aA",
   "status": 1,
   "blockNumber": 26,
   "effectiveGasPrice": 2037149553,
   "gasUsed": 21000
}
ok

----------------------------------------------------------------------
Ran 4 tests in 405.500s

OK
Emulator Down
==========Test #0=========
score: 4 of 4 (0 errors, 0 failures)
```

## Test Case Explain

We explain preliminaries of how the PoS emulator works to enable understanding of this test case. For the more detailed explain, please refer to the example `C04-ethereum-pos`.

The PoS emulator comprises `beacon-setup-node` and `etherum-nodes`. While the `ethereum-nodes` are the nodes to be the part of the blockchain running `geth` and `lighthouse` software, the `beacon-setup-node` is a node that generates the imperative config files to initialize the beacon chain.

When the emulator is up, it will go through the following steps to transit the ethereum consensus from POA to POS.

Step 1. `ethereum-nodes` : run a POA ethereum blockchain.
Step 2. `beacon-setup-node` : deploys a `deposit contract` inside the POA ethereum blockchain.
Step 3. `beacon-setup-node` : generates a genesis file for beacon chain. The genesis file is essenstial when running the lighthouse.
Step 4. `beacon-setup-node` : generates keys of the validtors that are activated from the genesis state.
Step 5. `beacon-setup-node` : distributes the files generated from step 3, 4 to each `ethereum-nodes`.
Step 6. `ethereum-nodes` : runs the beacon chain with the files from `beacon-setup-node` at step 5.
Step 7. When the `total_difficulty` is reached to the designated value(in this example `terminal_total_difficulty` is 30.), the ethereum blockchain stops to build further blocks using POA consensus and starts to build the blocks using POS consensus with the beacon chain.

In this test script, it comprises 4 test cases: (1) `test_pos_geth_connection`, (2) `test_pos_contract_deployment`, (3) `test_pos_chain_merged`, and (4) `test_pos_send_transaction`.

Testcase (1) `test_pos_geth_connection` checks the result of `Step 1`.
Testcase (2) `test_pos_contract_deployment` checks the result of `Step 2`
Testcase (3) `test_pos_chain_merged` checks the result of `Step 7`.
Testcase (4) `test_pos_send_transaction` checks if the PoS Etheruem blockchain runs well by sending a transaction.

### (1) `test_pos_geth_connection`

This case tests if the geth node is up or not by connecting to the geth http server. When the geth node is up, it also host a http server to enable the interaction with the blockchain through the HTTP APIs. So, in this test case, we assume that the geth http is opened, the geth node is running as we expected.

In this script, it tries to connect with 3 geth nodes: `10.151.0.72, 10.152.0.72, and 153.0.72` for 600 seconds. If it fails to connect, it waits 20 seconds and then retries. And if the connection is still failed after the 600 seconds, we estimate the node failed to run the geth node. The reason why we keep trying to connect is that a certain amount of time is needed to run all the emulator nodes and for each nodes to start a geth.

```python
def test_pos_geth_connection(self):
        url_1 = 'http://10.151.0.72:8545'
        url_2 = 'http://10.152.0.72:8545'
        url_3 = 'http://10.153.0.72:8545'

        i = 1
        current_time = time.time()
        while True:
            printLog("\n==========Trial {}==========".format(i))
            if time.time() - current_time > 600:
                printLog("TimeExhausted: 600 sec")
            try:
                self.wallet1.connectToBlockchain(url_1, isPOA=True)
                printLog("Connection Succeed: ", url_1)
                self.wallet2.connectToBlockchain(url_2, isPOA=True)
                printLog("Connection Succeed: ", url_2)
                self.wallet3.connectToBlockchain(url_3, isPOA=True)
                printLog("Connection Succeed: ", url_3)
                break
            except Exception as e:
                printLog(e)
                time.sleep(20)
                i += 1
        self.assertTrue(self.wallet1._web3.isConnected())
        self.assertTrue(self.wallet2._web3.isConnected())
        self.assertTrue(self.wallet3._web3.isConnected())
```

### (2) `test_pos_contract_deployment`

This test case confirm that the contract for the validator deposit is deployed successfully. As a part of the transition from POA to POS, it is essential to deploy the deposit contract that is used to stake Ethereum to join the network as a validator in PoS ethereum. If it fails to deploy the contract, it cannot proceed to the next step for `The Merge` in the emulator. The `beacon-setup-node` is the node that calls the geth API from one of the signer node to deploy the deposit contract. Once the contract is deployed, the contract address will be recorded inside the container as a file named `contract_address.txt`.

In this script, it checks the content of the `contract_address.txt` file every 10 seconds. If this file contains the address of the contract, we assume that the deployment is succeeded. For the investigation purpose, it also gives the `latest blockNumber` and `txpool` information as well.

```python
def test_pos_contract_deployment(self):
    client = docker.from_env()
    all_containers = client.containers.list()
    beacon_setup_container:container
    contract_deployed = False
    for container in all_containers:
        labels = container.attrs['Config']['Labels']
        if 'BeaconSetup' in labels.get('org.seedsecuritylabs.seedemu.meta.displayname', ''):
            beacon_setup_container = container
    web3_list = [(self.wallet1._url, self.wallet1._web3),
                    (self.wallet2._url, self.wallet2._web3),
                    (self.wallet3._url, self.wallet3._web3) ]

    while True:
        latestBlockNumber = self.wallet1._web3.eth.getBlock('latest').number
        printLog("\n========================================")
        printLog("Waiting for contract deployment...")
        printLog("current blockNumber : ", latestBlockNumber)
        for ip, web3 in web3_list:
            printLog("Total in txpool: {} ({})".format(len(web3.geth.txpool.content().pending), ip))
        if latestBlockNumber == 20:
            break
        result = str(beacon_setup_container.exec_run("cat contract_address.txt").output, 'utf-8')
        if 'Deposit contract address:' in result:
            printLog("++++Deposit Succeed++++")
            printLog(result)
            contract_deployed = True
            break
        time.sleep(10)
    self.assertTrue(contract_deployed)
```

### (3) `test_pos_chain_merged`

In this example, the ttd(terminal total difficulty) is set to 30, which means that the blockchain no longer builds new block when the total difficulty reach to this value until it merges with beaconchain and transits to POS consensus. In PoA etheruem blockchain, the difficulty is increased by 2 on average. So, blockchain will stop when the block number is 15 (15\*2=30(ttd)). Using this base knowledge, we assume that the consensus transition from POA to POS is succeeded if block number is over 17. Otherwise, the blockNumber will not increase from 15-17. In this script, it checks the blockNumber every 20 seconds. If the blockNumber is over 17, it assume that the chains are merged. On the other hand, if the blochNumber is not over 17 for 600 seconds, it returns a fail result.

```python
def test_pos_chain_merged(self):
    start_time = time.time()
    isMerged = False
    printLog("\n========================================")
    printLog("Terminal total difficulty is set to 30.")
    printLog("The blockNumber will not increase from 15, if the merge is failed.")
    printLog("So we will assume that the blockNumber is over 17, the merge is succeed.")
    printLog("========================================")
    while True:
        latestBlockNumber = self.wallet1._web3.eth.getBlock('latest').number
        printLog("current blockNumber : ", latestBlockNumber)
        if latestBlockNumber > 17:
            isMerged = True
            break
        if time.time() - start_time > 600:
            break
        time.sleep(20)
    self.assertTrue(isMerged)
```

### (4) `test_pos_send_transaction`

After the merge, we check the blockchain is operated well by testing the send_transaction. It tries to send a simple transaction that transfer a 0.1 Ethereum. We decide it succeed if it receives the transaction receipt and its status code is 1.

```
def test_pos_send_transaction(self):
    recipient = self.wallet1.getAccountAddressByName('Bob')
    txhash = self.wallet1.sendTransaction(recipient, 0.1, sender_name='David', wait=True, verbose=False)
    self.assertTrue(self.wallet1.getTransactionReceipt(txhash)["status"], 1)
```
