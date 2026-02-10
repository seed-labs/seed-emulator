import os
import sys
import tempfile
import unittest

# Add parent directory (mcp-server) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedops.ops import OpsService
from seedops.store import SeedOpsStore


class FakeExecResult:
    def __init__(self, exit_code: int, output: bytes):
        self.exit_code = exit_code
        self.output = output


class FakeContainer:
    def __init__(self, *, exec_exit: int = 0, exec_out: str = "", logs_out: str = ""):
        self._exec_exit = exec_exit
        self._exec_out = exec_out.encode("utf-8")
        self._logs_out = logs_out.encode("utf-8")

    def exec_run(self, cmd, demux=False):
        return FakeExecResult(self._exec_exit, self._exec_out)

    def logs(self, tail=200, since=None):
        return self._logs_out


class FakeContainers:
    def __init__(self, mapping: dict[str, FakeContainer]):
        self._mapping = mapping

    def get(self, name: str) -> FakeContainer:
        return self._mapping[name]


class FakeDockerClient:
    def __init__(self, mapping: dict[str, FakeContainer]):
        self.containers = FakeContainers(mapping)


class FakeWorkspaces:
    def __init__(self, nodes, docker_client):
        self._nodes = nodes
        self._docker_client = docker_client

    def list_nodes(self, workspace_id, selector=None):
        return self._nodes

    def get_docker_client(self):
        return self._docker_client


class TestSeedOpsOpsBatch(unittest.TestCase):
    def test_ops_exec_and_logs(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))

            nodes = [
                {"node_id": "as150/router0", "container_name": "c1"},
                {"node_id": "as151/router0", "container_name": "c2"},
            ]

            docker_client = FakeDockerClient(
                {
                    "c1": FakeContainer(exec_exit=0, exec_out="OK", logs_out="LOG1"),
                    "c2": FakeContainer(exec_exit=126, exec_out="ERR", logs_out="LOG2"),
                }
            )
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.exec("ws1", selector={}, command="echo hi", parallelism=2, max_output_chars=2)
            self.assertEqual(result["counts"]["total"], 2)
            self.assertEqual(result["counts"]["ok"], 1)
            self.assertEqual(result["counts"]["fail"], 1)
            # output truncated
            self.assertIn("truncated", result["results"][0]["output"] + result["results"][1]["output"])

            logs = ops.logs("ws1", selector={}, tail=10, parallelism=2, max_output_chars=100)
            self.assertEqual(logs["counts"]["total"], 2)
            self.assertEqual(logs["counts"]["ok"], 2)
            self.assertEqual(len(logs["logs"]), 2)


if __name__ == "__main__":
    unittest.main()

