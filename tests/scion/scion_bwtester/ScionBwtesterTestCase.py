#!/usr/bin/env python3

import time
import unittest as ut
from tests.scion import ScionTestCase

class ScionBwtesterTestCase(ScionTestCase):
    """!
    @brief Test the S03-bandwidth-test example.
    """
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(13)
        cls.printLog("Wait 60 seconds for beaconing")
        time.sleep(60)

    def setUp(self):
        super().setUp()
        self.bwtesters = {}
        for cntr in self.containers:
            if "bwtest" in cntr.name:
                asn, _, ip = cntr.name.split('-')
                asn = asn.lstrip('as').rstrip('h')
                self.bwtesters[f"1-{asn}"] = (ip, cntr)

    def bwtester_conn_test(self, container, server: str) -> bool:
        ec, output = container.exec_run(f"scion-bwtestclient -s {server}:40002")
        self.printLog(f"CMD: scion-bwtestclient -s {server}:40002")
        self.printLog(output.decode())
        return ec == 0

    def test_paths(self):
        """Check whether all SCION paths are up.
        """
        tests = [
            ("1-150", "1-151", "1-150 1-152? 1-151", 2),
            ("1-151", "1-152", "1-151 1-150? 1-152", 2),
            ("1-152", "1-150", "1-152 1-151? 1-150", 2),
            ("1-153", "1-150", "0*", 1),
            ("1-153", "1-151", "0*", 2),
            ("1-153", "1-152", "0*", 2),
        ]
        self.printLog(f"\n-------- Test SCION paths --------")
        for src, dst, pred, expected_paths in tests:
            _, cntr = self.bwtesters[src]
            ok, paths = self.scion_path_test(cntr, dst, pred=pred, ret_paths=True)
            self.assertTrue(ok)
            self.assertEqual(len(paths), expected_paths)

    def test_bwtester(self):
        """Test connectivity between bandwidth test servers and clients.
        """
        for server_ia, (server_ip, server) in self.bwtesters.items():
            for _, client in self.bwtesters.values():
                self.printLog(f"\n-------- Test BW {client.name} -> {server.name} --------")
                self.assertTrue(self.bwtester_conn_test(client, f"{server_ia},{server_ip}"))

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_paths'))
        test_suite.addTest(cls('test_bwtester'))
        return test_suite


if __name__ == "__main__":
    test_suite = ScionBwtesterTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ScionBwtesterTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ScionBwtesterTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
