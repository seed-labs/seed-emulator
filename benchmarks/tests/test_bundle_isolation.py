"""Contracts for exclusive, auditable Bundle Compose sessions."""

import json
from pathlib import Path
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator.bundle.isolation import BundleRunIsolator  # noqa: E402


class FakeIsolator(BundleRunIsolator):
    active_projects = set()

    def _prepare_runtime_context(self):
        self.runtime_context.mkdir(parents=True)
        self.runtime_compose_file.write_text(
            "services:\n  node:\n    image: example\n", encoding="utf-8"
        )
        octet = 10 if self.session_id.startswith("1") else 20
        if self.session_id == "0123456789":
            octet = 30
        self.network_map = {"10.0.0.0/24": f"10.128.{octet}.0/24"}
        self.report["network_rebindings"] = dict(self.network_map)

    def _run(self, argv, timeout=None):
        values = list(argv)
        if values[:2] == ["docker", "ps"]:
            return 0, "abc123\n" if self.project in self.active_projects else ""
        if values[:2] == ["docker", "inspect"]:
            return 0, f"/{self.project}-node-1|sha256:image|{self.project}|node\n"
        if values[:2] == ["docker", "compose"]:
            if "up" in values:
                self.active_projects.add(self.project)
            if "down" in values:
                self.active_projects.discard(self.project)
            return 0, "ok"
        raise AssertionError(values)


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    output = root / "generated" / "declarative" / "isolation_topology" / "output"
    output.mkdir(parents=True)
    (output / "docker-compose.yml").write_text(
        yaml.safe_dump({
            "name": "decl_isolation_topology",
            "services": {"node": {"image": "example"}},
            "networks": {"lan": {"ipam": {"config": [{"subnet": "10.0.0.0/24"}]}}},
        }),
        encoding="utf-8",
    )
    workspace = root / "reports" / "isolated"
    isolator = FakeIsolator(
        root, "isolation_topology", "isolation_request", workspace,
        session_id="0123456789",
    )
    capabilities = {
        "topology_id": "isolation_topology",
        "assets": [{
            "service": "node", "container": "fixed-node", "address": "10.0.0.2"
        }],
        "fault_component_bindings": {
            "docker_network_disconnected": [{
                "docker_network": "decl_isolation_topology_net_lan0",
                "container": "fixed-node",
                "peer_container": "fixed-node",
            }],
        },
    }
    with isolator:
        runtime = isolator.capabilities(capabilities)
        assert runtime["runtime_session"]["isolation"] == "parallel"
        runtime_container = runtime["assets"][0]["container"]
        assert runtime_container == f"{isolator.project}-node-1"
        assert runtime["assets"][0]["address"] == "10.128.30.2"
        assert runtime["fault_component_bindings"][
            "docker_network_disconnected"
        ][0]["container"] == runtime_container
        assert runtime["fault_component_bindings"][
            "docker_network_disconnected"
        ][0]["peer_container"] == runtime_container
        assert runtime["runtime_session"]["container_services"][runtime_container] == "node"
        assert runtime["fault_component_bindings"][
            "docker_network_disconnected"
        ][0]["docker_network"].startswith(isolator.project + "_")
        assert isolator.project in isolator.active_projects
    evidence = json.loads((workspace / "isolation.json").read_text())
    assert evidence["status"] == "cleaned"
    assert evidence["cleanup_verified"] is True
    assert evidence["runtime_compose_removed"] is True
    assert evidence["runtime_context_removed"] is True
    assert isolator.project not in isolator.active_projects

    # Two sessions from the same compiled topology own distinct container and
    # network identities and can remain active concurrently.
    first = FakeIsolator(
        root, "isolation_topology", "parallel_first", root / "reports" / "first",
        session_id="1111111111",
    )
    second = FakeIsolator(
        root, "isolation_topology", "parallel_second", root / "reports" / "second",
        session_id="2222222222",
    )
    with first:
        first_runtime = first.capabilities(capabilities)
        with second:
            second_runtime = second.capabilities(capabilities)
            assert first.project != second.project
            assert first_runtime["assets"][0]["container"] != (
                second_runtime["assets"][0]["container"]
            )
            assert first_runtime["assets"][0]["address"] != (
                second_runtime["assets"][0]["address"]
            )
            assert set(first_runtime["runtime_session"]["network_rebindings"].values()).isdisjoint(
                second_runtime["runtime_session"]["network_rebindings"].values()
            )
            assert len(FakeIsolator.active_projects) == 2
        assert first.project in FakeIsolator.active_projects
    assert not FakeIsolator.active_projects

print("bundle isolation tests passed")
