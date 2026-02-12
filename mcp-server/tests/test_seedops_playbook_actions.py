import os
import sys
import tempfile
import time
import unittest

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


class RecordingOps:
    def __init__(self):
        self.commands = []

    def exec(self, workspace_id: str, *, selector, command: str, timeout_seconds=30, parallelism=20, max_output_chars=8000):
        self.commands.append(command)
        return {
            "command": command,
            "command_hash": "deadbeef",
            "backend": "sdk",
            "counts": {"total": 1, "ok": 1, "fail": 0},
            "fail_reasons": {},
            "results": [{"node_id": "as150/router0", "ok": True, "exit_code": 0, "output": "OK"}],
        }

    def logs(self, workspace_id: str, *, selector, tail=200, since_seconds=0, parallelism=20, max_output_chars=8000):
        raise AssertionError("Unexpected logs call")

    def bgp_summary(self, workspace_id: str, *, selector):
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


class TestSeedOpsPlaybookActions(unittest.TestCase):
    def test_parse_requires_action_specific_args(self):
        with self.assertRaises(ValueError):
            parse_playbook_yaml(
                """
version: 1
name: bad
defaults:
  selector: {}
steps:
  - action: ping
"""
            )

        with self.assertRaises(ValueError):
            parse_playbook_yaml(
                """
version: 1
name: bad
defaults:
  selector: {}
steps:
  - action: inject_fault
    selector: {}
"""
            )

    def test_playbook_actions_call_ops_exec(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            ws = store.create_workspace("lab1")
            artifacts = ArtifactManager(base_dir=os.path.join(td, "data"), store=store)
            ops = RecordingOps()

            mgr = JobManager(store=store, workspaces=FakeWorkspaces(), ops=ops, artifacts=artifacts)
            job = mgr.start_playbook(
                ws.workspace_id,
                playbook_yaml="""
version: 1
name: actions
defaults:
  selector: {}
  timeout_seconds: 5
steps:
  - action: ping
    id: p
    dst: 1.1.1.1
    count: 2
  - action: traceroute
    id: t
    dst: 8.8.8.8
  - action: inject_fault
    id: f
    fault_type: packet_loss
    params: "20"
  - action: capture_evidence
    id: e
    evidence_type: routing_snapshot
""",
            )

            final = _wait_for_job(store, job.job_id, timeout_seconds=5.0)
            self.assertIsNotNone(final)
            self.assertEqual(final.status, "succeeded")

            self.assertEqual(len(ops.commands), 4)
            self.assertEqual(ops.commands[0], "ping -c 2 1.1.1.1")
            self.assertIn("traceroute -n 8.8.8.8", ops.commands[1])
            self.assertIn("tracepath -n 8.8.8.8", ops.commands[1])
            self.assertIn("tc qdisc add dev eth0 root netem loss 20%", ops.commands[2])
            self.assertIn("ip route", ops.commands[3])
            self.assertIn("birdc", ops.commands[3])


if __name__ == "__main__":
    unittest.main()

