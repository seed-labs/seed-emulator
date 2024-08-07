#!/usr/bin/env python3

import time
import unittest as ut

from tests.scion import ScionTestCase

class ScionBgpMixedTestCase(ScionTestCase):
    """!
    @brief Test the S02-scion-bgp-mixed example.
    """
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(22)
        cls.printLog("Wait 60 seconds for beaconing")
        time.sleep(60)

    def setUp(self):
        super().setUp()
        self.ases = [(1, 150), (1, 151), (1, 152), (1, 153), (2, 160), (2, 161)]
        self.cses = {}
        for cntr in self.containers:
            if "cs" in cntr.name:
                asn, _, ip = cntr.name.split('-')
                asn = asn.lstrip('as').rstrip('h')
                if int(asn) < 160:
                    ia = f"1-{asn}"
                else:
                    ia = f"2-{asn}"
                self.cses[cntr.name] = (ia, ip, cntr)

    def test_bgp_connections(self):
        """Test whether all control services can reach each other using their IP addresses directly.
        """
        for ia, ip, _ in self.cses.values():
            if ia == "2-161":
                dst = ip
                break
        for name, (_, _, cntr) in self.cses.items():
            self.printLog(f"\n-------- Test IP reachability from {name} --------")
            self.assertTrue(self.ping_test(cntr, dst))

    def test_scion_connections(self):
        """Test whether all control services can reach each other using their SCION addresses.
        """
        for name, (_, _, cntr) in self.cses.items():
            self.printLog(f"\n-------- Test SCION reachability from {name} --------")
            for ia in self.ases:
                self.assertTrue(self.scion_path_test(cntr, "{}-{}".format(*ia)))
            for ia, ip, _ in self.cses.values():
                self.assertTrue(self.scion_ping_test(cntr, f"{ia},{ip}"))

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_bgp_connections'))
        test_suite.addTest(cls('test_scion_connections'))
        return test_suite


if __name__ == "__main__":
    test_suite = ScionBgpMixedTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ScionBgpMixedTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ScionBgpMixedTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
