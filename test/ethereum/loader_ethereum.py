from importlib.abc import Loader
from operator import le
import os
import unittest

from simplejson import load

loader = unittest.TestLoader()
ethereumTestSuite = loader.discover("./cases",pattern='test_*.py')

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    os.chdir(os.getcwd()+"/cases")
    testResult = runner.run(ethereumTestSuite)
    print("Ethereum Unit Testing")
    print(testResult)
    # testResult.wasSuccessful
    # passSign = len(testResult.errors) == 0 and len(testResult.failures) == 0
    if testResult.wasSuccessful:
        print('\033[32m'+'PASS' + '\033[0m')
    else:
        if len(testResult.errors) != 0:
            print('\033[93m'+'================== Error ==================' + '\033[0m')
            for index, error in enumerate(testResult.errors):
                print("Error-{}".format(index+1))
                print(error[0])
                print(error[1])
        if len(testResult.failures) != 0:
            print('\033[91m'+'==================Failure==================' + '\033[0m')
            for index, failure in enumerate(testResult.failures):
                print("Failure-{}".format(index+1))
                print(failure[0])
                print(failure[1])