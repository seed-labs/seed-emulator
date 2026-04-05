import os
import sys
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.selectors import filter_nodes, match_selector


class TestSeedOpsSelectors(unittest.TestCase):
    def test_node_id_selector_matches_exact_nodes(self):
        nodes = [
            {"node_id": "as151/host_0", "asn": 151, "node_name": "host_0", "role": "Host"},
            {"node_id": "as202/dns-auth-gmail", "asn": 202, "node_name": "dns-auth-gmail", "role": "Host"},
            {"node_id": "as202/host_0", "asn": 202, "node_name": "host_0", "role": "Host"},
        ]

        selected = filter_nodes(
            nodes,
            {"node_id": ["as151/host_0", "as202/dns-auth-gmail"], "role": ["Host"]},
        )

        self.assertEqual(
            [node["node_id"] for node in selected],
            ["as151/host_0", "as202/dns-auth-gmail"],
        )
        self.assertTrue(match_selector(nodes[0], {"node_id": ["as151/host_0"]}))
        self.assertFalse(match_selector(nodes[2], {"node_id": ["as151/host_0", "as202/dns-auth-gmail"]}))


if __name__ == "__main__":
    unittest.main()
