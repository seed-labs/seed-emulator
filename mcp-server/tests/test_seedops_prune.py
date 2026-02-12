import os
import sys
import tempfile
import time
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.artifacts import ArtifactManager
from seedops.store import SeedOpsStore


class TestSeedOpsPrune(unittest.TestCase):
    def test_prune_events_and_snapshots(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")

            for i in range(10):
                store.insert_event(ws.workspace_id, level="info", event_type="test", message=f"e{i}", data={"i": i})

            deleted = store.prune_events(ws.workspace_id, keep_last=3)
            self.assertGreaterEqual(deleted, 7)
            events = store.list_events(ws.workspace_id, since_ts=0, limit=200)
            self.assertEqual(len(events), 3)

            for i in range(8):
                store.insert_snapshot(ws.workspace_id, snapshot_type="inventory_summary", data={"i": i})

            deleted_s = store.prune_snapshots(ws.workspace_id, snapshot_type="inventory_summary", keep_last=2)
            self.assertGreaterEqual(deleted_s, 6)
            snaps = store.list_snapshots(ws.workspace_id, snapshot_type="inventory_summary", since_ts=0, limit=200)
            self.assertEqual(len(snaps), 2)

    def test_prune_terminal_jobs_and_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")
            artifacts = ArtifactManager(base_dir=os.path.join(td, "data"), store=store)

            for i in range(3):
                job = store.create_job(ws.workspace_id, kind="playbook", name=f"job{i}")
                store.update_job(job.job_id, status="succeeded", finished_at=int(time.time()), message="done")
                artifacts.write_json(workspace_id=ws.workspace_id, job_id=job.job_id, name=f"out{i}", data={"i": i})

            to_prune = store.list_terminal_job_ids_to_prune(ws.workspace_id, keep_last=1)
            self.assertEqual(len(to_prune), 2)

            artifact_rows = store.list_artifacts_for_job_ids(to_prune)
            self.assertEqual(len(artifact_rows), 2)
            paths = [a.path for a in artifact_rows]
            artifact_ids = [a.artifact_id for a in artifact_rows]

            file_counts = artifacts.delete_files(artifact_rows)
            self.assertEqual(file_counts["deleted"], 2)
            for p in paths:
                self.assertFalse(os.path.exists(p))

            db_counts = store.delete_jobs_and_related(to_prune)
            self.assertEqual(db_counts["jobs_deleted"], 2)
            self.assertEqual(db_counts["artifacts_deleted"], 2)

            for aid in artifact_ids:
                self.assertIsNone(store.get_artifact(aid))


if __name__ == "__main__":
    unittest.main()

