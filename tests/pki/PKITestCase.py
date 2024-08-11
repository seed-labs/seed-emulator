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
        cls.wait_until_all_containers_up(19)
        cls.containers: List[Container] = cls.containers
        
    def test_root_cert_installed(self):
        for container in self.containers:
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') is None:
                continue
            # CA will install its own root cert
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') == "ca1":
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_0.pem")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_1.pem")
                self.assertNotEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') == "ca2":
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_0.pem")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_1.pem")
                self.assertEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.asn') == "150":
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_0.pem")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_1.pem")
                self.assertNotEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.asn') == "151":
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_0.pem")
                self.assertNotEqual(code, 0)
                code, _ = container.exec_run("ls /etc/ssl/certs/SEEDEMU_Internal_Root_CA_1.pem")
                self.assertEqual(code, 0)
                continue

    def test_web_cert_issued(self):
        for container in self.containers:
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') is None:
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.role') == "Route Server":
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.role') == "Router":
                continue
            # CA will install its own root cert
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') == "ca1":
                code, _ = container.exec_run("curl https://user1.internal")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("curl https://user2.internal")
                self.assertNotEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.nodename') == "ca2":
                code, _ = container.exec_run("curl https://user1.internal")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("curl https://user2.internal")
                self.assertEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.asn') == "150":
                code, _ = container.exec_run("curl https://user1.internal")
                self.assertEqual(code, 0)
                code, _ = container.exec_run("curl https://user2.internal")
                self.assertNotEqual(code, 0)
                continue
            if container.labels.get('org.seedsecuritylabs.seedemu.meta.asn') == "151":
                code, _ = container.exec_run("curl https://user1.internal")
                self.assertNotEqual(code, 0)
                code, _ = container.exec_run("curl https://user2.internal")
                self.assertEqual(code, 0)
                continue

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

