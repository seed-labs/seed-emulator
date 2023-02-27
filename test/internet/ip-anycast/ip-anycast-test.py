#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
import os
import getopt
import sys
import docker
import time

class IPAnyCastTest(ut.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = docker.from_env()
        init_container_count = len(cls.client.containers.list())
        os.system("/bin/bash ./emulator-code/run.sh 2> /dev/null &")
        while True:
            printLog("##################################################")
            printLog("###### Waiting until all containers up : 64 ######")
            cls.containers = cls.client.containers.list()
            cur_container_count = len(cls.containers) - init_container_count
            printLog("current containers counts : ", cur_container_count)
            if cur_container_count == 64:
                break
            time.sleep(10)
        time.sleep(10)
        for container in cls.containers:
            if "10.150.0.71" in container.name:
                cls.source_host = container
            if "as180r-router0" in container.name:
                cls.router0_180 = container
            if "as180r-router1" in container.name:
                cls.router1_180 = container
        return super().setUpClass()
        
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("/bin/bash ./emulator-code/down.sh 2> /dev/null")
        
        return super().tearDownClass()
    
    def test_ip_anycast(self):
        printLog("\n######### Test ip anycast #########")
        ip = "10.180.0.100"
        self.ping_test(ip, 0)

    def test_ip_anycast_router0(self):
        printLog("\n######### Test router0 #########")

        

        # Disable all bgp peers
        self.router0_180.exec_run("birdc dis u_as3")
        self.router0_180.exec_run("birdc dis u_as4")

        self.router1_180.exec_run("birdc dis u_as2")
        self.router1_180.exec_run("birdc dis u_as3")
        time.sleep(10)


        printLog("######### ping test expected result : failed #########")
        ip = "10.180.0.100"
        printLog("ip : {}".format(ip))
        self.ping_test(ip, 1)

        # Enable only router1
        printLog("######### enable router0 bgp peer #########")
        self.router1_180.exec_run("birdc en u_as3")
        time.sleep(10)
        printLog("######### ping test expected result : success #########")
        self.ping_test(ip, 0)

    def test_ip_anycast_router1(self):
        printLog("\n######### Test router1 #########")

        # Disable all bgp peers
        self.router0_180.exec_run("birdc dis u_as3")
        self.router0_180.exec_run("birdc dis u_as4")

        self.router1_180.exec_run("birdc dis u_as2")
        self.router1_180.exec_run("birdc dis u_as3")
        time.sleep(10)


        printLog("######### ping test expected result : failed #########")
        ip = "10.180.0.100"
        printLog("ip : {}".format(ip))
        self.ping_test(ip, 1)

        # Enable only router1
        printLog("######### enable router1 bgp peer #########")
        self.router1_180.exec_run("birdc en u_as3")
        time.sleep(10)
        printLog("######### ping test expected result : success #########")
        self.ping_test(ip, 0)

        
    def ping_test(self, ip, expected_exit_code=0):
        exit_code, output = self.source_host.exec_run("ping -c 3 {}".format(ip))
        if expected_exit_code == 0: printLog("ping test {} Succeed".format(ip))
        else: printLog("ping test {} Failed".format(ip))
        self.assertEqual(exit_code, expected_exit_code)

    

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
        test_suite.addTest(IPAnyCastTest('test_ip_anycast'))
        test_suite.addTest(IPAnyCastTest('test_ip_anycast_router0'))
        test_suite.addTest(IPAnyCastTest('test_ip_anycast_router1'))
        res = ut.TextTestRunner(verbosity=2).run(test_suite)

        succeed = "succeed" if res.wasSuccessful() else "failed"
        os.system("mv ./test_log/log ./test_log/test_%d/log_%s"%(i, succeed))

        printLog("Emulator Down")
        result.append(res)

    
    for count, res in enumerate(result):
        printLog("==========Test #%d========="%count)
        num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
        printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
