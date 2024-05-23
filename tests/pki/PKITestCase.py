#!/usr/bin/env python3
# encoding: utf-8

import unittest as ut
from tests import SeedEmuTestCase
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from docker.models.containers import Container

class PKITestCase(SeedEmuTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(17)
        cls.containers: List[Container] = cls.containers
        
    def test_root_cert_installed(self):
        for container in self.containers:
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') is None:
                continue
            code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA.pem")
            self.assertEqual(code, 0)

    def test_web_cert_issued(self):
        for container in self.containers:
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') is None:
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.role') == "Route Server":
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.role') == "Router":
                continue
            code, _ = container.exec_run("curl https://user.internal")
            self.assertEqual(code, 0)

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_root_cert_installed'))
        test_suite.addTest(cls('test_web_cert_issued'))
        return test_suite

if __name__ == "__main__":
    test_suite = PKITestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    PKITestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    PKITestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))

