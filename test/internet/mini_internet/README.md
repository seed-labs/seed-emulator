# Unit Test for Mini Internet

## Overview

The `MiniInternetTestCase.py` performs a unit test for `example/B00-mini-internet`. In this script, it consists of 4 testcases: (1) `test_internet_connection`, (2) `test_customized_ip_address`, and (3) `test_real_world_as`.

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./MiniInternetTestCase.py
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

In this test script, it comprises 8 test cases: (1) `test_internet_connection`, (2) `test_customized_ip_address`, and (3) `test_real_world_as`.


Testcase (1) `test_internet_connection` ping to all other containers and test it is not failed.
Testcase (2) `test_customized_ip_address` ping to cutomized ip and test if a ip customization works.
Testcase (3) `test_real_world_as` ping to a real world ip that belongs to the enable real world AS (11872). 