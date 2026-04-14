import os
import sys
import tempfile
import time
import unittest
import base64
from unittest.mock import patch

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.artifacts import ArtifactManager
from seedops.jobs import JobManager
from seedops.store import SeedOpsStore


class FakeWorkspaces:
    def list_nodes(self, workspace_id: str, selector=None):
        return [
            {"node_id": "as150/router0", "container_name": "c0"},
            {"node_id": "as150/host0", "container_name": "c1"},
        ]

    def refresh(self, workspace_id: str, redacted: bool = False):
        return {
            "workspace_id": workspace_id,
            "counts": {"containers_seen": 0, "nodes_parsed": 0, "missing_containers": 0},
            "roles": {},
            "asns": [],
            "sample_nodes": [],
        }


class FakeOps:
    def exec(self, *args, **kwargs):
        raise AssertionError("Unexpected ops_exec call")

    def logs(self, *args, **kwargs):
        raise AssertionError("Unexpected ops_logs call")

    def routing_protocol_summary(self, *args, **kwargs):
        raise AssertionError("Unexpected routing_protocol_summary call")

    def bgp_summary(self, *args, **kwargs):
        raise AssertionError("Unexpected bgp_summary call")


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


class TestSeedOpsPcapCapture(unittest.TestCase):
    def test_pcap_capture_writes_pcap_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")
            artifacts = ArtifactManager(base_dir=os.path.join(td, "data"), store=store)
            mgr = JobManager(store=store, workspaces=FakeWorkspaces(), ops=FakeOps(), artifacts=artifacts)

            def fake_capture_pcap_to_file(**kwargs):
                out_path = kwargs["out_path"]
                with open(out_path, "wb") as f:
                    f.write(b"PCAPDATA")
                return {"exit_code": 0, "bytes_written": 8, "truncated": False, "timed_out": False, "stderr_head": ""}

            with patch("seedops.jobs._capture_pcap_to_file", side_effect=fake_capture_pcap_to_file):
                job = mgr.start_playbook(
                    ws.workspace_id,
                    playbook_yaml="""
version: 1
name: pcap
defaults:
  selector: {}
steps:
  - action: pcap_capture
    id: cap
    duration_seconds: 1
    interface: any
    max_bytes: 1024
""",
                )

                final = _wait_for_job(store, job.job_id, timeout_seconds=5.0)
                self.assertIsNotNone(final)
                self.assertEqual(final.status, "succeeded")

                rows = store.list_artifacts(job.job_id, limit=20)
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(r.kind == "pcap" for r in rows))

                chunk = artifacts.read_chunk_base64(rows[0].artifact_id, offset=0, max_bytes=16)
                self.assertIsNotNone(chunk)
                self.assertGreater(chunk.bytes_read, 0)
                decoded = base64.b64decode(chunk.content_b64.encode("ascii"))
                self.assertIn(b"PCAP", decoded)


if __name__ == "__main__":
    unittest.main()
