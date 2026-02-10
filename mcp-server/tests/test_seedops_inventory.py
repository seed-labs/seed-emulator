import os
import sys
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.inventory import InventoryBuilder
from seedops.selectors import match_selector


class FakeContainer:
    def __init__(self, name: str, labels: dict[str, str]):
        self.name = name
        self.labels = labels


class TestSeedOpsInventory(unittest.TestCase):
    def test_parse_node_from_labels(self):
        labels = {
            "org.seedsecuritylabs.seedemu.meta.asn": "150",
            "org.seedsecuritylabs.seedemu.meta.nodename": "router0",
            "org.seedsecuritylabs.seedemu.meta.role": "BorderRouter",
            "org.seedsecuritylabs.seedemu.meta.class": "[\"Routing\"]",
            "org.seedsecuritylabs.seedemu.meta.loopback_addr": "10.0.0.1",
            "org.seedsecuritylabs.seedemu.meta.net.0.name": "net0",
            "org.seedsecuritylabs.seedemu.meta.net.0.address": "10.150.0.254/24",
            "org.seedsecuritylabs.seedemu.meta.net.1.name": "ix100",
            "org.seedsecuritylabs.seedemu.meta.net.1.address": "10.100.0.150/24",
        }
        c = FakeContainer("as150brd-router0-10.150.0.254", labels)

        inv = InventoryBuilder().build([c])
        self.assertEqual(len(inv.nodes), 1)

        node = inv.nodes[0]
        self.assertEqual(node["node_id"], "as150/router0")
        self.assertEqual(node["asn"], 150)
        self.assertEqual(node["role"], "BorderRouter")
        self.assertIn("Routing", node["classes"])
        self.assertEqual(node["container_name"], "as150brd-router0-10.150.0.254")
        self.assertEqual(len(node["interfaces"]), 2)

    def test_selector_matching(self):
        node = {
            "node_id": "as150/router0",
            "asn": 150,
            "node_name": "router0",
            "role": "BorderRouter",
            "classes": ["Routing"],
            "container_name": "as150brd-router0-10.150.0.254",
            "interfaces": [{"name": "net0", "address": "10.150.0.254/24"}, {"name": "ix100", "address": "10.100.0.150/24"}],
            "loopback": "10.0.0.1",
            "labels": {"k": "v"},
        }

        self.assertTrue(match_selector(node, {"asn": 150}))
        self.assertTrue(match_selector(node, {"asn": [150, 151]}))
        self.assertFalse(match_selector(node, {"asn": 151}))
        # Empty lists should match nothing (safer than matching everything).
        self.assertFalse(match_selector(node, {"asn": []}))

        self.assertTrue(match_selector(node, {"role": "BorderRouter", "network": "ix100"}))
        self.assertFalse(match_selector(node, {"role": "Host"}))
        self.assertFalse(match_selector(node, {"role": []}))

        self.assertTrue(match_selector(node, {"class": "Routing"}))
        self.assertFalse(match_selector(node, {"class": "WebService"}))
        self.assertFalse(match_selector(node, {"network": []}))


if __name__ == "__main__":
    unittest.main()
