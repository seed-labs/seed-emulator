#!/usr/bin/env python3
# encoding: utf-8

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import unittest as ut
from tests.SeedEmuTestCase import SeedEmuTestCase

class DNSTestCase(SeedEmuTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(4)
        cls.local_dns = None
        cls.client1 = None
        cls.auth_example = None
        cls.auth_rev = None
        for c in cls.containers:
            n = c.name
            if 'local-dns' in n or '10.151.0.53' in n:
                cls.local_dns = c
            if 'client1' in n:
                cls.client1 = c
        # Discover authoritative containers by scanning their bind configs
        for c in cls.containers:
            ec, _ = c.exec_run("sh -lc 'test -f /etc/bind/named.conf.zones && grep -q " + '"zone \\\"example32.com.\\\""' + " /etc/bind/named.conf.zones'")
            if ec == 0:
                cls.auth_example = c
            ec, _ = c.exec_run("sh -lc 'test -f /etc/bind/named.conf.zones && grep -q " + '"zone \\\"in-addr.arpa.\\\""' + " /etc/bind/named.conf.zones'")
            if ec == 0:
                cls.auth_rev = c
        return

    def _ok(self, container, cmd):
        ec, _ = container.exec_run(cmd)
        return ec == 0

    def test_authoritative_basic(self):
        self.assertIsNotNone(self.auth_example)
        self.assertTrue(self._ok(self.auth_example, "test -f /etc/bind/named.conf.zones"))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'zone \"example32.com.\"' /etc/bind/named.conf.zones"))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'SOA' /etc/bind/zones/example32.com."))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'NS ' /etc/bind/zones/example32.com."))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'A 10.151.0.7' /etc/bind/zones/example32.com."))

    def test_caching_forward_and_resolvconf(self):
        self.assertIsNotNone(self.local_dns)
        self.assertIsNotNone(self.client1)
        self.assertTrue(self._ok(self.client1, "grep -q 'nameserver 10.151.0.53' /etc/resolv.conf"))
        self.assertTrue(self._ok(self.local_dns, "grep -q 'zone \"example32.com.\"' /etc/bind/named.conf.local"))
        self.assertTrue(self._ok(self.local_dns, "grep -q 'forwarders' /etc/bind/named.conf.local"))
        ec, _ = self.client1.exec_run("ping -c 1 example32.com")
        self.assertEqual(ec, 0)

    def test_root_hints_recursive(self):
        self.assertIsNotNone(self.local_dns)
        self.assertTrue(self._ok(self.local_dns, "test -f /usr/share/dns/root.hints"))
        self.assertTrue(self._ok(self.local_dns, "test -f /etc/bind/db.root"))
        self.assertTrue(self._ok(self.local_dns, "grep -q 'NS ' /etc/bind/db.root || grep -q -E '[0-9]+(\\.[0-9]+){3}' /usr/share/dns/root.hints"))

    def test_reverse_ptr_files(self):
        self.assertIsNotNone(self.auth_rev)
        self.assertTrue(self._ok(self.auth_rev, "grep -q 'PTR' /etc/bind/zones/in-addr.arpa."))

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_authoritative_basic'))
        test_suite.addTest(cls('test_caching_forward_and_resolvconf'))
        test_suite.addTest(cls('test_root_hints_recursive'))
        test_suite.addTest(cls('test_reverse_ptr_files'))
        return test_suite

if __name__ == "__main__":
    test_suite = DNSTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    DNSTestCase.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    DNSTestCase.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
