import os
import sys
import tempfile
import time
import unittest
import base64

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.artifacts import ArtifactManager
from seedops.jobs import JobManager
from seedops.playbooks import parse_playbook_yaml
from seedops.store import SeedOpsStore


class FakeWorkspaces:
    def refresh(self, workspace_id: str):
        return {
            "workspace_id": workspace_id,
            "counts": {"containers_seen": 0, "nodes_parsed": 0, "missing_containers": 0},
            "roles": {},
            "asns": [],
            "sample_nodes": [],
        }

    def list_nodes(self, workspace_id: str, selector=None):
        return [{"node_id": "as150/router0"}]


class FakeOps:
    def exec(self, workspace_id: str, *, selector, command: str, timeout_seconds=30, parallelism=20, max_output_chars=8000):
        return {
            "command": command,
            "command_hash": "deadbeef",
            "backend": "sdk",
            "counts": {"total": 1, "ok": 1, "fail": 0},
            "fail_reasons": {},
            "results": [{"node_id": "as150/router0", "ok": True, "exit_code": 0, "output": "OK"}],
        }

    def logs(self, workspace_id: str, *, selector, tail=200, since_seconds=0, parallelism=20, max_output_chars=8000):
        return {"counts": {"total": 1, "ok": 1, "fail": 0}, "fail_reasons": {}, "logs": []}

    def bgp_summary(self, workspace_id: str, *, selector):
        return {
            "backend": "sdk",
            "counts": {"nodes": 1, "nodes_ok": 1, "nodes_error": 0, "bgp_up": 1, "bgp_down": 0},
            "nodes": [],
        }


def _wait_for_job(store: SeedOpsStore, job_id: str, *, timeout_seconds: float = 5.0):
    deadline = time.monotonic() + timeout_seconds
    last = None
    while time.monotonic() < deadline:
        j = store.get_job(job_id)
        last = j
        if j and j.status not in {"queued", "running", "cancel_requested"}:
            return j
        time.sleep(0.05)
    return last


class TestSeedOpsPhase2Jobs(unittest.TestCase):
    def test_playbook_parse_validate(self):
        pb = parse_playbook_yaml(
            """
version: 1
name: test
defaults:
  selector: {}
steps:
  - action: workspace_refresh
  - action: ops_exec
    selector: {}
    command: "echo hi"
"""
        )
        self.assertEqual(pb.version, 1)
        self.assertEqual(pb.name, "test")
        self.assertEqual(len(pb.steps), 2)

        with self.assertRaises(ValueError):
            parse_playbook_yaml(
                """
version: 1
steps:
  - action: ops_exec
    selector: {}
"""
            )

    def test_playbook_job_and_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")
            artifacts = ArtifactManager(base_dir=os.path.join(td, "data"), store=store)

            mgr = JobManager(store=store, workspaces=FakeWorkspaces(), ops=FakeOps(), artifacts=artifacts)

            job = mgr.start_playbook(
                ws.workspace_id,
                playbook_yaml="""
version: 1
name: demo
defaults:
  selector: {}
steps:
  - action: workspace_refresh
    id: refresh
    save_as: refresh_result
  - action: ops_exec
    id: exec
    selector: {}
    command: "echo hi"
    save_as: exec_result
  - action: sleep
    seconds: 0.1
""",
            )

            final = _wait_for_job(store, job.job_id, timeout_seconds=5.0)
            self.assertIsNotNone(final)
            self.assertEqual(final.status, "succeeded")
            self.assertEqual(final.progress_current, 3)

            arts = store.list_artifacts(job.job_id)
            self.assertEqual(len(arts), 2)
            names = {a.name for a in arts}
            self.assertIn("refresh_result", names)
            self.assertIn("exec_result", names)

            read = artifacts.read(arts[0].artifact_id, max_chars=2000)
            self.assertIsNotNone(read)
            self.assertIn("{", read.content)

            chunk = artifacts.read_chunk_base64(arts[0].artifact_id, offset=0, max_bytes=64)
            self.assertIsNotNone(chunk)
            self.assertGreater(chunk.bytes_read, 0)
            decoded = base64.b64decode(chunk.content_b64.encode("ascii"))
            self.assertIn(b"{", decoded)

            steps = store.list_job_steps(job.job_id, since_step_id=0, limit=200)
            self.assertTrue(any(s.event_type == "step.finished" for s in steps))

    def test_collector_job_and_snapshots(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")
            artifacts = ArtifactManager(base_dir=os.path.join(td, "data"), store=store)

            mgr = JobManager(store=store, workspaces=FakeWorkspaces(), ops=FakeOps(), artifacts=artifacts)
            job = mgr.start_collector(ws.workspace_id, interval_seconds=1, selector={}, include_bgp_summary=True)

            # Let at least one tick happen.
            time.sleep(0.2)
            mgr.cancel_job(job.job_id)

            final = _wait_for_job(store, job.job_id, timeout_seconds=5.0)
            self.assertIsNotNone(final)
            self.assertIn(final.status, {"canceled", "failed"})

            snaps = store.list_snapshots(ws.workspace_id, limit=50)
            self.assertTrue(any(s.snapshot_type == "inventory_summary" for s in snaps))


if __name__ == "__main__":
    unittest.main()
