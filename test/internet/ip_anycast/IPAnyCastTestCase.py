#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
import os
import time
from test import SeedEmuTestCase


class IPAnyCastTestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(64)
        for container in cls.containers:
            if "10.150.0.71" in container.name:
                cls.source_host = container
            if "as180r-router0" in container.name:
                cls.router0_180 = container
            if "as180r-router1" in container.name:
                cls.router1_180 = container
        return 
        
    @classmethod
    def tearDownClass(cls) -> None:
        '''
        A classmethod to destruct the some thing after this test case is finished.
        For this test case, it will down the containers and remove the networks of this test case
        '''
        os.system("/bin/bash ./emulator-code/down.sh 2> /dev/null")
        
        return super().tearDownClass()
    
    def test_ip_anycast(self):
        self.printLog("\n-------- Test ip anycast --------")
        ip = "10.180.0.100"
        self.assertTrue(self.ping_test(self.source_host, ip, 0))
        

    def test_ip_anycast_router0(self):
        self.printLog("\n-------- Test router0 --------")

        # Disable all bgp peers
        self.router0_180.exec_run("birdc dis u_as3")
        self.router0_180.exec_run("birdc dis u_as4")

        self.router1_180.exec_run("birdc dis u_as2")
        self.router1_180.exec_run("birdc dis u_as3")
        time.sleep(10)

        self.printLog("ping test expected result : failed")
        ip = "10.180.0.100"
        self.printLog("ip : {}".format(ip))
        self.assertTrue(self.ping_test(self.source_host, ip, 1))

        # Enable only router1
        self.printLog("-------- enable router0 bgp peer --------")
        self.router1_180.exec_run("birdc en u_as3")
        time.sleep(10)
        self.printLog("ping test expected result : success ")
        self.assertTrue(self.ping_test(self.source_host, ip, 0))

    def test_ip_anycast_router1(self):
        self.printLog("\n-------- Test router1 --------")

        # Disable all bgp peers
        self.router0_180.exec_run("birdc dis u_as3")
        self.router0_180.exec_run("birdc dis u_as4")

        self.router1_180.exec_run("birdc dis u_as2")
        self.router1_180.exec_run("birdc dis u_as3")
        time.sleep(10)


        self.printLog("ping test expected result : failed ")
        ip = "10.180.0.100"
        self.printLog("ip : {}".format(ip))
        self.assertTrue(self.ping_test(self.source_host, ip, 1))

        # Enable only router1
        self.printLog("-------- enable router1 bgp peer --------")
        self.router1_180.exec_run("birdc en u_as3")
        time.sleep(10)
        self.printLog("ping test expected result : success")
        self.assertTrue(self.ping_test(self.source_host, ip, 0))

    

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(IPAnyCastTestCase('test_ip_anycast'))
        test_suite.addTest(IPAnyCastTestCase('test_ip_anycast_router0'))
        test_suite.addTest(IPAnyCastTestCase('test_ip_anycast_router1'))
        return test_suite


if __name__ == "__main__":
    test_suite = IPAnyCastTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    IPAnyCastTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    IPAnyCastTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
        
