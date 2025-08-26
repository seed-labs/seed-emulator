#!/usr/bin/env python3

from internet import IPAnyCastTestCase, MiniInternetTestCase, HostMgmtTestCase
from ethereum import EthereumPOATestCase, EthereumPOSTestCase, EthereumPOWTestCase
from scion import ScionBgpMixedTestCase, ScionBwtesterTestCase, ScionLargeASNTestCase
from options import SEEDEmuOptionSystemTestCase
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
parser.add_argument("--basic", action="store_true", help="Run basic tests")
parser.add_argument("--internet", action="store_true", help="Run internet tests")
parser.add_argument("--blockchain", action="store_true", help="Run blockchain tests")
parser.add_argument("--scion", action="store_true", help="Run SCION tests")
args = parser.parse_args()

# Set an environment variable
os.environ['platform'] = args.platform

test_case_list = [
]

blockchain_tests = [
    EthereumPOATestCase,
    EthereumPOSTestCase,
    EthereumPOWTestCase,
    ChainlinkPOATestCase,
    EthUtilityPOATestCase
]

scion_tests = [
    ScionLargeASNTestCase,
    ScionBgpMixedTestCase,
    ScionBwtesterTestCase
]

basic_tests = [
    MiniInternetTestCase,
    # SEEDEmuOptionSystemTestCase,
        ]

internet_tests = [
    KuboTestCase,
    KuboUtilFuncsTestCase,
    IPAnyCastTestCase,
    HostMgmtTestCase,
    PKITestCase,
    DottedDictTestCase,
    TrafficGeneratorTestCase
        ]

if args.basic:
    test_case_list.extend(basic_tests)
if args.internet:
    test_case_list.extend(internet_tests)
if args.blockchain:
    test_case_list.extend(blockchain_tests)
if args.scion:
    test_case_list.extend(scion_tests)

if args.ci:
    test_case_list = [
        MiniInternetTestCase,
        IPAnyCastTestCase,
        HostMgmtTestCase,
        # ScionBgpMixedTestCase,
        # ScionBwtesterTestCase,
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
