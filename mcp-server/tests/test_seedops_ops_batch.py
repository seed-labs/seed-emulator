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


class ScriptedContainer(FakeContainer):
    def __init__(self, script_map: dict[str, tuple[int, str]]):
        super().__init__()
        self._script_map = script_map

    def exec_run(self, cmd, demux=False):
        script = cmd[-1] if isinstance(cmd, list) and cmd else str(cmd)
        for needle, result in self._script_map.items():
            if needle in str(script):
                exit_code, output = result
                return FakeExecResult(exit_code, output.encode("utf-8"))
        return FakeExecResult(127, b"unsupported")


class FakeContainerNoStream(FakeContainer):
    def logs(self, tail=200, since=None, **kwargs):
        if "stream" in kwargs:
            raise AssertionError("ops.logs should not request Docker log streaming")
        return super().logs(tail=tail, since=since)


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

    def get_visibility(self, workspace_id):
        return {"workspace_id": workspace_id, "allowed_selector": {}, "redacted_fields": []}


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

    def test_ops_logs_avoids_streaming(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient({"c1": FakeContainerNoStream(logs_out="ROUTER LOG")})
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            logs = ops.logs("ws1", selector={}, tail=10, parallelism=1, max_output_chars=100)

            self.assertEqual(logs["counts"]["ok"], 1)
            self.assertEqual(logs["logs"][0]["log"], "ROUTER LOG")

    def test_routing_protocol_summary_auto_falls_back_to_frr(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient(
                {
                    "c1": ScriptedContainer(
                        {
                            "birdc show protocols": (127, "birdc: not found"),
                            "vtysh -c 'show bgp summary'": (
                                0,
                                "Neighbor        V         AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd\n"
                                "10.0.0.1        4        65001      10      10      0   0    0 00:10:12        7\n",
                            ),
                        }
                    )
                }
            )
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.routing_protocol_summary("ws1", selector={}, backend="auto")

            self.assertEqual(result["counts"]["nodes_ok"], 1)
            self.assertEqual(result["counts"]["bgp_up"], 1)
            self.assertEqual(result["nodes"][0]["backend"], "frr")
            self.assertEqual(result["backend_counts"]["frr"], 1)

    def test_routing_protocol_summary_auto_prefers_frr_when_bgpd_is_running(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient(
                {
                    "c1": ScriptedContainer(
                        {
                            "seedops-routing-probe": (
                                0,
                                "cmd:birdc=1\n"
                                "cmd:vtysh=1\n"
                                "proc:bird\n"
                                "proc:bgpd\n"
                                "proc:zebra\n",
                            ),
                            "vtysh -c 'show bgp summary'": (
                                0,
                                "BGP router identifier 10.0.0.1, local AS number 65000\n"
                                "Neighbor        V         AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd\n"
                                "10.0.0.1        4        65001      10      10      0   0    0 00:10:12        7\n",
                            ),
                            "birdc show protocols": (
                                0,
                                "name     proto    table    state  since       info\n"
                                "peer1    BGP      master   up     2026-04-04  Established\n",
                            ),
                        }
                    )
                }
            )
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.routing_protocol_summary("ws1", selector={}, backend="auto")

            self.assertEqual(result["counts"]["nodes_ok"], 1)
            self.assertEqual(result["counts"]["bgp_up"], 1)
            self.assertEqual(result["nodes"][0]["backend"], "frr")
            self.assertEqual(result["backend_counts"]["frr"], 1)

    def test_routing_protocol_summary_auto_ignores_unusable_frr_output(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient(
                {
                    "c1": ScriptedContainer(
                        {
                            "seedops-routing-probe": (
                                0,
                                "cmd:birdc=1\n"
                                "cmd:vtysh=1\n"
                                "proc:bird\n"
                                "proc:zebra\n"
                                "proc:ldpd\n",
                            ),
                            "birdc show protocols": (
                                0,
                                "name     proto    table    state  since       info\n"
                                "peer1    BGP      master   up     2026-04-04  Established\n",
                            ),
                            "vtysh -c 'show bgp summary'": (0, "bgpd is not running\n"),
                        }
                    )
                }
            )
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.routing_protocol_summary("ws1", selector={}, backend="auto")

            self.assertEqual(result["counts"]["nodes_ok"], 1)
            self.assertEqual(result["counts"]["bgp_up"], 1)
            self.assertEqual(result["nodes"][0]["backend"], "bird")
            self.assertEqual(result["backend_counts"]["bird"], 1)

    def test_routing_protocol_summary_explicit_frr_reports_error_when_bgpd_is_not_running(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient(
                {
                    "c1": ScriptedContainer(
                        {
                            "vtysh -c 'show bgp summary'": (0, "bgpd is not running\n"),
                        }
                    )
                }
            )
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.routing_protocol_summary("ws1", selector={}, backend="frr")

            self.assertEqual(result["counts"]["nodes_error"], 1)
            self.assertEqual(result["nodes"][0]["backend"], "frr")
            self.assertFalse(result["nodes"][0]["ok"])
            self.assertIn("bgpd is not running", result["nodes"][0]["error"])

    def test_routing_looking_glass_reports_unsupported_when_no_backend_matches(self):
        with tempfile.TemporaryDirectory() as td:
            store = SeedOpsStore(os.path.join(td, "seedops.db"))
            nodes = [{"node_id": "as150/router0", "container_name": "c1"}]
            docker_client = FakeDockerClient({"c1": ScriptedContainer({})})
            workspaces = FakeWorkspaces(nodes, docker_client)
            ops = OpsService(store=store, workspaces=workspaces)

            result = ops.routing_looking_glass("ws1", selector={}, prefix="10.0.0.0/24", backend="auto")

            self.assertEqual(result["counts"]["nodes_error"], 1)
            self.assertEqual(result["nodes"][0]["backend"], "unsupported")
            self.assertFalse(result["nodes"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
