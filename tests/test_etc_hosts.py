import unittest

from seedemu.core import Emulator
from seedemu.layers import Base, EtcHosts


class EtcHostsTests(unittest.TestCase):
    def render_hosts(self, layer):
        emulator = Emulator()
        base = Base()
        autonomous_system = base.createAutonomousSystem(150)
        autonomous_system.createNetwork("net0", "10.150.0.0/24")
        host = autonomous_system.createHost("host0").joinNetwork("net0", "10.150.0.71")
        host.addHostName("existing.seed.net")
        router = autonomous_system.createRouter("router0").joinNetwork("net0", "10.150.0.254")
        emulator.addLayer(base)
        emulator.addLayer(layer)
        emulator.render()
        return host, router

    def content(self, node):
        return node.getFile("/tmp/etc-hosts").get()[1].splitlines()

    def test_custom_record_preserves_generated_entries(self):
        layer = EtcHosts()
        self.assertIs(layer.addRecord("xyz.seed.net", "10.154.0.30"), layer)
        host, router = self.render_hosts(layer)
        lines = self.content(host)
        self.assertIn("10.154.0.30 xyz.seed.net", lines)
        self.assertTrue(any("existing.seed.net" in line and line.startswith("10.150.0.71 ")
                            for line in lines))
        self.assertNotIn("/tmp/etc-hosts", [file.get()[0] for file in router.getFiles()])

    def test_all_nodes_receive_custom_records(self):
        host, router = self.render_hosts(
            EtcHosts(only_hosts=False).addRecord("xyz.seed.net", "10.154.0.30")
        )
        for node in (host, router):
            self.assertIn("10.154.0.30 xyz.seed.net", self.content(node))

    def test_custom_record_can_be_updated(self):
        layer = EtcHosts().addRecord("xyz.seed.net", "10.154.0.30")
        layer.addRecord("xyz.seed.net", "10.154.0.31")
        host, _ = self.render_hosts(layer)
        self.assertIn("10.154.0.31 xyz.seed.net", self.content(host))
        self.assertNotIn("10.154.0.30 xyz.seed.net", self.content(host))

    def test_ipv6_custom_record(self):
        host, _ = self.render_hosts(EtcHosts().addRecord("ipv6.seed.net", "2001:db8::30"))
        self.assertIn("2001:db8::30 ipv6.seed.net", self.content(host))

    def test_invalid_records_are_rejected(self):
        for hostname in ("", "two names", "name\nother", "name#comment"):
            with self.subTest(hostname=hostname), self.assertRaises(ValueError):
                EtcHosts().addRecord(hostname, "10.154.0.30")
        for address in ("invalid", "10.154.0.999", "10.154.0.30\nother"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                EtcHosts().addRecord("xyz.seed.net", address)

    def test_default_behavior_has_no_custom_records(self):
        host, _ = self.render_hosts(EtcHosts())
        self.assertTrue(any("existing.seed.net" in line for line in self.content(host)))
        self.assertFalse(any("xyz.seed.net" in line for line in self.content(host)))


if __name__ == "__main__":
    unittest.main()
