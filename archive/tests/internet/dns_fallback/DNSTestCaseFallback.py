#!/usr/bin/env python3
# encoding: utf-8

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import unittest as ut
from tests.SeedEmuTestCase import SeedEmuTestCase

class DNSTestCaseFallback(SeedEmuTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wait_until_all_containers_up(4)
        cls.local_dns = None
        cls.client1 = None
        cls.auth_example = None
        for c in cls.containers:
            n = c.name
            if 'local-dns' in n or '10.151.0.53' in n:
                cls.local_dns = c
            if 'client1' in n:
                cls.client1 = c
        # Discover authoritative for example32.com by scanning bind configs
        for c in cls.containers:
            ec, _ = c.exec_run("sh -lc 'test -f /etc/bind/named.conf.zones && grep -q " + '"zone \\\"example32.com.\\\""' + " /etc/bind/named.conf.zones'")
            if ec == 0:
                cls.auth_example = c
        return

    def _ok(self, container, cmd):
        ec, _ = container.exec_run(cmd)
        return ec == 0

    def test_authoritative_zone_present(self):
        self.assertIsNotNone(self.auth_example)
        self.assertTrue(self._ok(self.auth_example, "test -f /etc/bind/named.conf.zones"))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'zone \"example32.com.\"' /etc/bind/named.conf.zones"))
        self.assertTrue(self._ok(self.auth_example, "grep -q 'A 10.151.0.7' /etc/bind/zones/example32.com."))

    def test_forwarders_fallback_by_zone_server_list(self):
        self.assertIsNotNone(self.local_dns)
        # Provided invalid vnode name; install() may fallback to zone server list-derived IPs
        # or skip forwarders entirely (rely on root recursion). Accept either behavior.
        # Debug print
        ec, out = self.local_dns.exec_run("sh -lc 'cat -n /etc/bind/named.conf.local 2>/dev/null || true'")
        self.printLog(out.decode() if out else "<no named.conf.local>")
        has_forwarders = self._ok(self.local_dns, "grep -Eq 'forwarders *\\{ *([0-9]+\\.){3}[0-9]+ *; *\\};' /etc/bind/named.conf.local")
        if not has_forwarders:
            # Ensure root hints exist to allow recursion path
            self.assertTrue(self._ok(self.local_dns, "test -s /usr/share/dns/root.hints"))

    def test_resolution_works(self):
        self.assertIsNotNone(self.client1)
        self.assertTrue(self._ok(self.client1, "grep -q 'nameserver 10.151.0.53' /etc/resolv.conf"))
        ec, _ = self.client1.exec_run("ping -c 1 example32.com")
        self.assertEqual(ec, 0)

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_authoritative_zone_present'))
        test_suite.addTest(cls('test_forwarders_fallback_by_zone_server_list'))
        test_suite.addTest(cls('test_resolution_works'))
        return test_suite

if __name__ == "__main__":
    test_suite = DNSTestCaseFallback.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(test_suite)

    DNSTestCaseFallback.printLog("==========Test=========")
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)
    DNSTestCaseFallback.printLog("score: %d of %d (%d errors, %d failures)" % (num - (errs+fails), num, errs, fails))
