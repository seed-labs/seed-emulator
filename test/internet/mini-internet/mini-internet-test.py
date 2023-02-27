#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
import os
import getopt
import sys
import docker
import time

class MiniInternetTest(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = docker.from_env()
        init_container_count = len(cls.client.containers.list())
        os.system("/bin/bash ./emulator-code/run.sh 2> /dev/null &")
        while True:
            printLog("##################################################")
            printLog("###### Waiting until all containers up : 60 ######")
            cls.containers = cls.client.containers.list()
            cur_container_count = len(cls.containers) - init_container_count
            printLog("current containers counts : ", cur_container_count)
            if cur_container_count == 60:
                break
            time.sleep(10)
        time.sleep(10)
        for container in cls.containers:
            if "10.150.0.71" in container.name:
                cls.source_host = container
                break
        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("/bin/bash ./emulator-code/down.sh 2> /dev/null")
        
        return super().tearDownClass()
    
    def test_internet_connection(self):
        asns = [151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
        for asn in asns:
            printLog("\n######### ping test #########")
            ip = "10.{}.0.254".format(asn)
            printLog("ip : {}".format(ip))
            self.ping_test(ip)

    def test_customized_ip_address(self):
        printLog("\n######### customized ip test #########")
        printLog("ip : 10.154.0.129")
        self.ping_test("10.154.0.129")

    def test_real_world_as(self):
        printLog("\n######### real world as test #########")
        printLog("real world as 11872")
        printLog("check real world ip : 128.230.64.1")
        self.ping_test("128.230.64.1")

    def test_vpn(self):
        return
        
    def ping_test(self, ip):
        exit_code, output = self.source_host.exec_run("ping -c 3 {}".format(ip))
        self.assertEqual(exit_code, 0)
        printLog("ping test {} succeed".format(ip))
    

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
        os.system("mkdir ./test_log/test_%d"%i)
        test_suite = ut.TestSuite()
        test_suite.addTest(MiniInternetTest('test_internet_connection'))
        test_suite.addTest(MiniInternetTest('test_customized_ip_address'))
        test_suite.addTest(MiniInternetTest('test_real_world_as'))
        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        os.system("mv ./test_log/log ./test_log/test_%d/log_%s"%(i, succeed))

        printLog("Emulator Down")
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
