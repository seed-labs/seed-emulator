import os
import sys
import tempfile
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.store import SeedOpsStore


class TestSeedOpsStore(unittest.TestCase):
    def test_workspace_crud_and_events(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "seedops.db")
            store = SeedOpsStore(db_path)

            ws = store.create_workspace("lab1")
            self.assertEqual(ws.name, "lab1")
            self.assertTrue(ws.workspace_id)

            items = store.list_workspaces()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].workspace_id, ws.workspace_id)

            got = store.get_workspace(ws.workspace_id)
            self.assertIsNotNone(got)
            self.assertEqual(got.name, "lab1")

            store.update_workspace_attach(
                ws.workspace_id,
                "compose",
                {"output_dir": "/tmp/output", "container_names": ["c1", "c2"], "label_prefix": "org.seedsecuritylabs.seedemu.meta."},
            )
            got2 = store.get_workspace(ws.workspace_id)
            self.assertIsNotNone(got2)
            self.assertEqual(got2.attach_type, "compose")
            self.assertIn("output_dir", got2.attach_config)

            eid = store.insert_event(ws.workspace_id, level="info", event_type="test.event", message="hello", data={"x": 1})
            events = store.list_events(ws.workspace_id, since_ts=0, limit=10)
            self.assertTrue(any(ev.event_id == eid for ev in events))


if __name__ == "__main__":
    unittest.main()

