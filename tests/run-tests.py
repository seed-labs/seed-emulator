#!/usr/bin/env python3

from internet import IPAnyCastTestCase, MiniInternetTestCase, HostMgmtTestCase
from ethereum import EthereumPOATestCase, EthereumPOSTestCase, EthereumPOWTestCase
from scion import ScionBgpMixedTestCase, ScionBwtesterTestCase
from kubo import KuboTestCase, KuboUtilFuncsTestCase, DottedDictTestCase
from pki import PKITestCase
from chainlink import ChainlinkPOATestCase
from traffic_generator import TrafficGeneratorTestCase
from ethUtility import EthUtilityPOATestCase
import argparse
import unittest
import os

parser = argparse.ArgumentParser()
parser.add_argument("platform", nargs='?', default="amd")
parser.add_argument("--ci", action='store_true', help="Run limited set of tests")
args = parser.parse_args()

# Set an environment variable
os.environ['platform'] = args.platform

test_case_list = [
    MiniInternetTestCase,
    IPAnyCastTestCase,
    HostMgmtTestCase,
    EthereumPOATestCase,
    EthereumPOSTestCase,
    EthereumPOWTestCase,
    ChainlinkPOATestCase,
    EthUtilityPOATestCase,
    ScionBgpMixedTestCase,
    ScionBwtesterTestCase,
    KuboTestCase,
    KuboUtilFuncsTestCase,
    DottedDictTestCase,
    PKITestCase,
    TrafficGeneratorTestCase
]

if args.ci:
    test_case_list = [
        MiniInternetTestCase,
        IPAnyCastTestCase,
        HostMgmtTestCase,
        ScionBgpMixedTestCase,
        ScionBwtesterTestCase,
        DottedDictTestCase,
        TrafficGeneratorTestCase
    ]

for test_case in test_case_list:
    test_suite = test_case.get_test_suite()
    res = unittest.TextTestRunner(verbosity=2).run(test_suite)
    test_case.printLog("==============================")
    test_case.printLog("{} Test Ends".format(test_case.__name__))
    test_case.printLog("==============================")

    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    test_case.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
