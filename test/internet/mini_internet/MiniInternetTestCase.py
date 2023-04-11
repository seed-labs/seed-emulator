#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from test import SeedEmuTestCase

class MiniInternetTestCase(SeedEmuTestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(60)
        for container in cls.containers:
            if "10.150.0.71" in container.name:
                cls.source_host = container
                break
        return 
        
    def test_internet_connection(self):
        asns = [151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
        for asn in asns:
            self.printLog("\n-------- ping test --------")
            ip = "10.{}.0.254".format(asn)
            self.printLog("ip : {}".format(ip))
            self.assertTrue(self.ping_test(self.source_host, ip))

    def test_customized_ip_address(self):
        self.printLog("\n-------- customized ip test --------")
        self.printLog("ip : 10.154.0.129")
        self.assertTrue(self.ping_test(self.source_host, "10.154.0.129"))

    def test_real_world_as(self):
        self.printLog("\n-------- real world as test --------")
        self.printLog("real world as 11872")
        self.printLog("check real world ip : 128.230.64.1")
        self.assertTrue(self.ping_test(self.source_host, "128.230.64.1"))

    def test_vpn(self):
        return
    

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_internet_connection'))
        test_suite.addTest(cls('test_customized_ip_address'))
        test_suite.addTest(cls('test_real_world_as'))
        return test_suite

if __name__ == "__main__":
    test_suite = MiniInternetTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    MiniInternetTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    MiniInternetTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
    
