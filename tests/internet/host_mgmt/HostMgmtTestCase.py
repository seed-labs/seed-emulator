#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from tests import SeedEmuTestCase
import re

def get_numbers_from_string(input_string):
    # Use regular expression to find all numbers in the string
    numbers = re.findall(r'\d+', input_string)
    return ''.join(numbers)

class HostMgmtTestCase(SeedEmuTestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(61)
        cls.hostnames = []
        for container in cls.containers:
            container_name = (container.name).split('-')
            if len(container_name) >= 3:
                asn, name = container_name[0], ''.join(container_name[1:-1])
                asn = get_numbers_from_string(asn)
                print(f"{asn}-{name}")
                cls.hostnames.append(f"{asn}-{name}")
            if "10.150.0.71" in container.name:
                cls.source_host = container
        return 
        
    def test_default_host_names(self):
        for hostname in self.hostnames:
            # Test only if the node role is host or router. If their role is ix and rs, 
            # it is natural that the normal host node is not able to connect to them. 
            if "router" in hostname or "host" in hostname or "webservice" in hostname:
                self.printLog("\n-------- ping test --------")
                self.printLog("hostname : {}".format(hostname))
                self.assertTrue(self.ping_test(self.source_host, hostname))

    def test_customized_host_names(self):
        self.printLog("\n-------- customized ip test --------")
        self.printLog("hostname : database.com")
        self.assertTrue(self.ping_test(self.source_host, "database.com"))
    

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_default_host_names'))
        test_suite.addTest(cls('test_customized_host_names'))
        return test_suite

if __name__ == "__main__":
    test_suite = HostMgmtTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    HostMgmtTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    HostMgmtTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
    
