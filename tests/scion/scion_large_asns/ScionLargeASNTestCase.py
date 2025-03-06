#!/usr/bin/env python3

import time
import unittest as ut

from seedemu.core.ScionAutonomousSystem import IA, ScionASN
from tests.scion import ScionTestCase


class ScionLargeASNTestCase(ScionTestCase):
    """!
    @brief Test the S02-scion-bgp-mixed example.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(5)
        cls.printLog("Wait 60 seconds for beaconing")
        time.sleep(60)

    def setUp(self):
        super().setUp()
        self.ases = [IA(1, 0x100001101), IA(1, 151)]
        self.cses = {}
        for cntr in self.containers:
            if "cs" in cntr.name:
                asn, _, ip = cntr.name.split("-")
                asn = ScionASN(int(asn.lstrip("as").rstrip("h")))
                self.cses[cntr.name] = (f"1-{asn}", ip, cntr)

    def test_scion_connections(self):
        """Test whether all control services can reach each other using their
        SCION addresses.
        """
        for name, (_, _, cntr) in self.cses.items():
            self.printLog(f"\n-------- Test SCION reachability from {name} --------")
            for ia in self.ases:
                self.assertTrue(self.scion_path_test(cntr, f"{ia}"))
            for ia, ip, _ in self.cses.values():
                self.assertTrue(self.scion_ping_test(cntr, f"{ia},{ip}"))

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls("test_scion_connections"))
        return test_suite


if __name__ == "__main__":
    test_suite = ScionLargeASNTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    ScionLargeASNTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    ScionLargeASNTestCase.printLog(
        "score: %d of %d (%d errors, %d failures)"
        % (num - (errs + fails), num, errs, fails)
    )
