from .internet import *
from .ethereum import *
import unittest

test_case_list = [
    MiniInternetTestCase,
    IPAnyCastTestCase,
    EthereumPOATestCase, 
    EthereumPOSTestCase,
    EthereumPOWTestCase ]

for test_case in test_case_list:
    test_suite = test_case.get_test_suite()
    res = unittest.TextTestRunner(verbosity=2).run(test_suite)

    test_case.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    test_case.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
            