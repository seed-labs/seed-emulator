# Unit Test for IP Any Cast

## Overview

The `IPAnyCastTestCase.py` performs a unit test for `example/B03-ip-anycast`. In this script, it consists of 4 testcases: (1) `test_ip_anycast`, (2) `test_ip_anycast_router0`, and (3) `test_ip_anycast_router1`.

## How to run

This unit testing have a loader to load all the ethereum service unit testing cases.

```sh
# Run the Test Script
./IPAnyCastTestCase.py
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

In this test script, it comprises 8 test cases: (1) `test_ip_anycast`, (2) `test_ip_anycast_router0`, and (3) `test_ip_anycast_router1`.

Testcase (1) `test_ip_anycast` ping to `10.180.0.100` and test it is not failed.
Testcase (2) `test_ip_anycast_router0` disable all routers and test if ping to `10.180.0.100` fails. Then, enable only router0 and test if ping to `10.180.0.100` works.
Testcase (3) `test_ip_anycast_router1` disable all routers and test if ping to `10.180.0.100` fails. Then, enable only router1 and test if ping to `10.180.0.100` works.