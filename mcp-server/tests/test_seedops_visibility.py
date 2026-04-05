import os
import sys
import tempfile
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.inventory import Inventory
from seedops.store import SeedOpsStore
from seedops.workspaces import WorkspaceManager


class TestSeedOpsVisibility(unittest.TestCase):
    def test_workspace_visibility_filters_and_redacts_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            manager = WorkspaceManager(store=store)
            ws = manager.create("lab1")

            nodes = [
                {
                    "node_id": "as150/router0",
                    "asn": 150,
                    "node_name": "router0",
                    "role": "Router",
                    "classes": ["Routing"],
                    "container_name": "r0",
                    "labels": {"env": "prod"},
                    "interfaces": [],
                },
                {
                    "node_id": "as151/router0",
                    "asn": 151,
                    "node_name": "router0",
                    "role": "Router",
                    "classes": ["Routing"],
                    "container_name": "r1",
                    "labels": {"env": "lab"},
                    "interfaces": [],
                },
            ]
            manager._cache[ws.workspace_id] = Inventory(
                nodes=nodes,
                by_node_id={node["node_id"]: node for node in nodes},
                updated_at=0,
            )

            visibility = manager.set_visibility(
                ws.workspace_id,
                allowed_selector={"asn": [151]},
                redacted_fields=["node_id", "container_name", "labels"],
            )

            self.assertEqual(visibility["allowed_selector"], {"asn": [151]})
            listed = manager.list_nodes(ws.workspace_id, selector={}, redacted=True)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["asn"], 151)
            self.assertNotIn("node_id", listed[0])
            self.assertNotIn("container_name", listed[0])
            self.assertNotIn("labels", listed[0])

            hidden = manager.get_node(ws.workspace_id, "as150/router0", redacted=True)
            self.assertIsNone(hidden)

            visible = manager.get_node(ws.workspace_id, "as151/router0", redacted=True)
            self.assertIsNotNone(visible)
            self.assertNotIn("node_id", visible)
            self.assertNotIn("container_name", visible)
            self.assertNotIn("labels", visible)


if __name__ == "__main__":
    unittest.main()
