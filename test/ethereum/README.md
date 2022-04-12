# Unit testing for EthereumSevice

## Overview

This folder contains the all unit testing cases for EthereumSevice using library [unittest](https://docs.python.org/3/library/unittest.html), a unit testing included in python. This unit testing will going to build and run the container for unit testing by asserting the output of command run on specific container.

This unit testing is an example to show how to write the unit test cases for seed-emulator.

## How to run

### Run all test cases

Before running the testing, you should make sure loading the environment of emulator.

```sh
source development.env
```

1. Run all test cases

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
python3 loader_ethereum.py
```

Then wait some time for testing, it may need half an hours to run all the case depend on the computer.

### Run single test cases

For example, we can run single test case `test_Run_POA`. 

1. Go to test cases folder

```sh
cd cases
```

2. Run the test case

```sh
python3 test_Run_POA.py
```

Then wait some time for testing, it may need 10 minutes to run this case depend on the computer.

## Folder Structure Explain

In side this case, there are two essential folders. 

`cases` for test cases python code.

`resources` for the resource for a single test case, normally it contains python code that defines the network for testing and some bash scripts to build and run the containers for testing. 

## How to write a Test Case

We are highly recommended to read the unittest document and learn the base concepts before starting reading the test case.

You could look at a well-commented test case example `cases/test_Run_POA.py` to learn how to write a test case.

## Test Cases

- test_EthAccount

    This test case test the EthAccount class in `Ethereum Service`. It will test do the methods work correctly, especially create account and import account.

- test_Genesis
    
    This test case test the Genesis class in `Ethereum Service`. It will test do the methods work correctly, especially for POA and POW genesis file content output.

- test_Run_POA

    This test case test a ethereum network only using Proof-Of-Authority consensus.

- test_Run_POW

    This test case test a ethereum network only using Proof-Of-Work consensus.

- test_Run_POA

    This test case test a ethereum network using both Proof-Of-Authority and Proof-Of-Work consensus.  

## Reference

1. [unittest document](https://docs.python.org/3/library/unittest.html)