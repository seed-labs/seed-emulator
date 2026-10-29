#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from seedemu import *
import shutil
import os
import getopt
import sys


class MultiPlatformTest(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.test_list = {
            "B06-blockchain" : (["blockchain.py"], ["output", "eth-states"])
        }
        cls.dummy_list = {
            "arm" : {
                        "39e016aa9e819f203ebc1809245a5818": "FROM handsonsecurity/seedemu-multiarch-router:buildx-latest",
                        "98a2693c996c2294358552f48373498d": "FROM handsonsecurity/seedemu-multiarch-base:buildx-latest",
                        "6aa6090a0b640f105845984c991134a9": "FROM handsonsecurity/seedemu-ethereum-arm64"
                    },
            "amd" : {
                        "39e016aa9e819f203ebc1809245a5818": "FROM handsonsecurity/seedemu-multiarch-router:buildx-latest",
                        "98a2693c996c2294358552f48373498d": "FROM handsonsecurity/seedemu-multiarch-base:buildx-latest",
                        "f1d53a66de3c35d8a921558f3b4bdbbd": "FROM handsonsecurity/seedemu-ethereum"
                    }
        }
        # This is my path
        cls.init_cwd = os.getcwd()

        cls.path = "../../examples"
        for dir, (scripts, outputs) in cls.test_list.items():
            path = os.path.join(cls.path, dir)
            os.chdir(path)
            file_list = os.listdir(os.curdir)
            for output in outputs:
                if output in file_list: 
                    if os.path.isdir(os.path.join(path, output)):   shutil.rmtree(output)
                    else:   os.remove(output)
            os.chdir(cls.init_cwd)
        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls.init_cwd)
        return super().tearDownClass()
    
    def arm_compile_test(self):
        for dir, (scripts, outputs) in self.test_list.items():
            printLog("######### {} Test #########".format(dir))
            path = os.path.join(self.path, dir)
            os.chdir(path)
            for script in scripts:
                os.system("./{} arm 2> /dev/null".format(script))
            for output in outputs:
                self.assertTrue(output in os.listdir(os.curdir))
            os.chdir(self.init_cwd)

    def arm_image_check(self):
        for dir, (scripts, outputs) in self.test_list.items():
            for filename, content in self.dummy_list['arm'].items():
                path = os.path.join(self.path, dir, "output/dummies", filename)
                # Open the file in read mode
                with open(path, 'r') as file:
                    # Read the first line
                    first_line = file.readline()

                    print(first_line)
                    print(content)

                    self.assertTrue(content.strip()==first_line.strip())

    def amd_compile_test(self):
        for dir, (scripts, outputs) in self.test_list.items():
            printLog("######### {} Test #########".format(dir))
            path = os.path.join(self.path, dir)
            os.chdir(path)
            for script in scripts:
                os.system("./{} amd 2> /dev/null".format(script))
            for output in outputs:
                self.assertTrue(output in os.listdir(os.curdir))
            os.chdir(self.init_cwd)

    def amd_image_check(self):
        for dir, (scripts, outputs) in self.test_list.items():
            for filename, content in self.dummy_list['amd'].items():
                path = os.path.join(self.path, dir, "output/dummies", filename)
                # Open the file in read mode
                with open(path, 'r') as file:
                    # Read the first line
                    first_line = file.readline()
                    
                    print(first_line)
                    print(content)

                    self.assertTrue(content.strip()==first_line.strip())



    
def get_arguments(argv, mapping):
    # Remove 1st argument from the list of command line arguments
    argumentList = argv[1:]

    # Options and long options
    options = "ht:"
    long_options = ["help", "times="]

    try:
        # Parsing argument
        arguments, values = getopt.getopt(argumentList, options, long_options)

        # checking each argument
        for arg, value in arguments:
            if arg in ("-h", "--help"):
                print ("Usage: test_script.py -t <times>")
                exit()

            elif arg in ("-t", "--times"):
                mapping['times'] = int(value)

    except getopt.error as err:
        print (str(err))

def printLog(*args, **kwargs):
    print(*args, **kwargs)
    with open('./test_log/log.txt','a') as file:
        print(*args, **kwargs, file=file)


if __name__ == "__main__":
    options = {}
    options['times'] = 1  # default sleeping time
    get_arguments(sys.argv, options)    
    result = []

    os.system("rm -rf test_log")
    os.system("mkdir test_log")
    
    for i in range(options['times']):
        test_suite = ut.TestSuite()
        test_suite.addTest(MultiPlatformTest('amd_compile_test'))
        test_suite.addTest(MultiPlatformTest('amd_image_check'))
        test_suite.addTest(MultiPlatformTest('arm_compile_test'))
        test_suite.addTest(MultiPlatformTest('arm_image_check'))
        
        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
