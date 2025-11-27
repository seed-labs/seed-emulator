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

### 2. Run Emulator Dynamic Test

A dynamic test including `internet`, `ethereum` and `email` runs containers from the emulator files and see if it performs a unit test inside a docker container dynamically using a `docker` python library.

```sh
# Run the Test Script
./run-test.py
```

The `run-test.py` runs multiple test suites including:
- Internet Protocols: `ip_anycast`, `mini_internet`
- DNS: `dns`, `dns_no_master`, `dns_fallback`
- Email: `email` (Comprehensive test for Postfix/Dovecot/Roundcube)
- Ethereum: `POW`, `POA`, `POS`

#### Check score of each test
```sh
$ cat test_result.txt | grep score
score: 3 of 3 (0 errors, 0 failures)
...
```

## Dynamic testcase folder structure
Each testcase has a format of folder as below. A `emulator-code/test-emulator.py` contains a python script for emulation file generation.

```sh
tests/internet/email/
├── emulator-code
│   └── test-emulator.py  <-- Copied from examples/internet/B29_email_dns/email_simple_v2.py
├── __init__.py
└── EmailTestCase.py      <-- Test logic
```
