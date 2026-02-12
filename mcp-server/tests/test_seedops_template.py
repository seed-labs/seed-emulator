import os
import sys
import tempfile
import time
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.artifacts import ArtifactManager
from seedops.jobs import JobManager
from seedops.store import SeedOpsStore
from seedops.template import TemplateError, render_value


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
        self.calls = []

    def exec(self, workspace_id: str, *, selector, command: str, timeout_seconds=30, parallelism=20, max_output_chars=8000):
        self.calls.append({"selector": selector, "command": command})
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


class TestSeedOpsTemplate(unittest.TestCase):
    def test_render_value_full_template_returns_typed(self):
        ctx = {"vars": {"obj": {"a": 1}, "arr": [10, 20], "k": {"x": "y"}}}
        self.assertEqual(render_value("{{ vars.obj }}", ctx), {"a": 1})
        self.assertEqual(render_value("{{ vars.arr[1] }}", ctx), 20)
        self.assertEqual(render_value("{{ vars.k['x'] }}", ctx), "y")

    def test_render_value_interpolation(self):
        ctx = {"vars": {"asn": 150, "name": "r0"}}
        self.assertEqual(render_value("as{{ vars.asn }}/{{ vars.name }}", ctx), "as150/r0")

    def test_render_value_recursive(self):
        ctx = {"vars": {"asn": 150}}
        v = {"selector": {"asn": "{{ vars.asn }}"}, "list": ["{{ vars.asn }}", 1]}
        self.assertEqual(render_value(v, ctx), {"selector": {"asn": 150}, "list": [150, 1]})

    def test_render_value_missing_key_raises(self):
        with self.assertRaises(TemplateError):
            render_value("{{ vars.missing }}", {"vars": {}})

    def test_playbook_job_renders_defaults_and_step_args(self):
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
name: templating
vars:
  asn: 150
  sel:
    asn: [150]
defaults:
  selector: "{{ vars.sel }}"
steps:
  - action: workspace_refresh
    id: refresh
  - action: ops_exec
    id: echo
    command: "echo {{ vars.asn }} {{ steps.refresh.summary.counts.nodes_parsed }}"
  - action: ops_exec
    id: override
    selector: "{{ vars.sel }}"
    command: "echo hi"
""",
            )

            final = _wait_for_job(store, job.job_id, timeout_seconds=5.0)
            self.assertIsNotNone(final)
            self.assertEqual(final.status, "succeeded")

            self.assertEqual(len(ops.calls), 2)
            self.assertEqual(ops.calls[0]["selector"], {"asn": [150]})
            self.assertEqual(ops.calls[0]["command"], "echo 150 0")
            self.assertEqual(ops.calls[1]["selector"], {"asn": [150]})
            self.assertEqual(ops.calls[1]["command"], "echo hi")


if __name__ == "__main__":
    unittest.main()

