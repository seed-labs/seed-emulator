# Unit Test for SEED Emulator

## Overview

The `test` folder contains 2 types of tests. First is compile-test and the second is dynamic test on Emulator service. 

## Test Environment
- os : ubuntu20.04
- python version : 3.8.10
- docker version : 20.10.21
- python package dependency : 
    pip3 install -r requirements.txt

## How to run

### 1. Run Compile test

Compile-test runs all example codes under `example` folder and confirm the codes run without an error and generate expected outputs. 

```sh
cd compile-test
./compile-test.py
```

#### Expected Result
```sh
...ommitted...
######### C00-hybrid-internet Test #########
######### C01-hybrid-dns-component Test #########
######### C02-hybrid-internet-with-dns Test #########
######### C03-bring-your-own-internet Test #########
######### C04-ethereum-pos Test #########
ok

----------------------------------------------------------------------
Ran 1 test in 59.980s

OK
==========Test #0=========
score: 1 of 1 (0 errors, 0 failures)
```


### 2. Run Emulator Dynamic Test

A dynamic test including `internet` and `ethereum` runs containers from the emulator files and see if it performs a unit test inside a docker container dynamically using a `docker` python library. For the Ethereum test,  we use `web3` python library as well.

```sh
# Run the Test Script
./run-test.py
```

The `run-test.py` runs `ip_anycast` and `mini_internet` tests in `internet` folder and `POW`, `POA`, and `POS`test in `ethereum` folder. A test result is not only printed out to the terminal also saved as a file named `test_result.txt` and each detailed test logs are located in a folder of each test. For example, a test log of `POA` is in `ethereum/POA/test_log` folder. 

```sh
test_log/
├── build_log
├── compile_log
├── containers_log
└── test_result.txt
```

#### Check score of each test
```sh
$ cat test_result.txt | grep score
score: 3 of 3 (0 errors, 0 failures)
score: 3 of 3 (0 errors, 0 failures)
score: 8 of 8 (0 errors, 0 failures)
score: 4 of 4 (0 errors, 0 failures)
score: 8 of 8 (0 errors, 0 failures)
```

## Dynamic testcase folder structure
Each testcase has a format of folder as below. A `emulator-code/test-emulator.py` contains a python script for emulation file generation. Each testcase has a format of folder as below. A `emulator-code/test-emulator.py` contains a python script for emulation file generation. 

```sh
$ tree mini_internet/
mini_internet/
├── emulator-code
│   └── test-emulator.py
├── __init__.py
└── MiniInternetTestCase.py
```

