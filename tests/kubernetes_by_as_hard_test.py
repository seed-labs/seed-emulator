#!/usr/bin/env python3

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from seedemu.compiler import KubernetesCompiler, SchedulingStrategy
from seedemu.core import Emulator
from seedemu.layers import Base, Routing, Ebgp


class KubernetesByAsHardCompilerTest(unittest.TestCase):
    def _build_emulator(self):
        emulator = Emulator()
        base = Base()
        routing = Routing()

        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createRouter("r0").joinNetwork("net0")
        as150.createHost("h0").joinNetwork("net0")

        as151 = base.createAutonomousSystem(151)
        as151.createNetwork("net0")
        as151.createRouter("r0").joinNetwork("net0")
        as151.createHost("h0").joinNetwork("net0")

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.render()
        return emulator

    def _read_deployments(self, manifest_path: Path):
        deployments = []
        for document in manifest_path.read_text(encoding="utf-8").split("\n---\n"):
            document = document.strip()
            if not document.startswith("{"):
                continue
            parsed = json.loads(document)
            if parsed.get("kind") == "Deployment":
                deployments.append(parsed)
        return deployments

    def _read_documents(self, manifest_path: Path):
        documents = []
        for document in manifest_path.read_text(encoding="utf-8").split("\n---\n"):
            stripped = document.strip()
            if not stripped:
                continue
            documents.append(yaml.safe_load(stripped))
        return documents

    def test_same_asn_uses_same_explicit_node_selector(self):
        emulator = self._build_emulator()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                compiler = KubernetesCompiler(
                    registry_prefix="",
                    namespace="seedemu-test",
                    use_multus=False,
                    internetMapEnabled=False,
                    scheduling_strategy=SchedulingStrategy.BY_AS_HARD,
                    node_labels={
                        "100": {"kubernetes.io/hostname": "node-a"},
                        "150": {"kubernetes.io/hostname": "node-a"},
                        "151": {"kubernetes.io/hostname": "node-b"},
                    },
                    image_pull_policy="IfNotPresent",
                )
                emulator.compile(compiler, tmp_dir, override=True)
                deployments = self._read_deployments(Path(tmp_dir) / "k8s.yaml")
        finally:
            os.chdir(original_cwd)

        selectors = {}
        for deployment in deployments:
            labels = deployment["spec"]["template"]["metadata"]["labels"]
            asn = labels["seedemu.io/asn"]
            selectors.setdefault(asn, []).append(deployment["spec"]["template"]["spec"]["nodeSelector"])

        self.assertTrue(selectors["150"])
        self.assertTrue(all(selector == {"kubernetes.io/hostname": "node-a"} for selector in selectors["150"]))
        self.assertTrue(all(selector == {"kubernetes.io/hostname": "node-b"} for selector in selectors["151"]))

    def test_missing_as_mapping_fails_fast(self):
        emulator = self._build_emulator()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                compiler = KubernetesCompiler(
                    registry_prefix="",
                    namespace="seedemu-test",
                    use_multus=False,
                    internetMapEnabled=False,
                    scheduling_strategy=SchedulingStrategy.BY_AS_HARD,
                    node_labels={"150": {"kubernetes.io/hostname": "node-a"}},
                    image_pull_policy="IfNotPresent",
                )
                with self.assertRaises(AssertionError):
                    emulator.compile(compiler, tmp_dir, override=True)
        finally:
            os.chdir(original_cwd)

    def test_by_as_hard_uses_bridge_for_internal_links_and_macvlan_for_ix(self):
        emulator = Emulator()
        base = Base()
        routing = Routing()
        ebgp = Ebgp()

        base.createInternetExchange(100)

        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createRouter("r0").joinNetwork("net0").joinNetwork("ix100")

        as151 = base.createAutonomousSystem(151)
        as151.createNetwork("net0")
        as151.createRouter("r0").joinNetwork("net0").joinNetwork("ix100")

        ebgp.addRsPeer(100, 150)
        ebgp.addRsPeer(100, 151)

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.addLayer(ebgp)
        emulator.render()

        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                compiler = KubernetesCompiler(
                    registry_prefix="",
                    namespace="seedemu-test",
                    use_multus=True,
                    internetMapEnabled=False,
                    scheduling_strategy=SchedulingStrategy.BY_AS_HARD,
                    node_labels={
                        "100": {"kubernetes.io/hostname": "node-a"},
                        "150": {"kubernetes.io/hostname": "node-a"},
                        "151": {"kubernetes.io/hostname": "node-b"},
                    },
                    cni_type="macvlan",
                    cni_master_interface="ens2",
                    image_pull_policy="IfNotPresent",
                )
                emulator.compile(compiler, tmp_dir, override=True)
                documents = self._read_documents(Path(tmp_dir) / "k8s.yaml")
        finally:
            os.chdir(original_cwd)

        nad_by_name = {
            document["metadata"]["name"]: json.loads(document["spec"]["config"])
            for document in documents
            if document.get("kind") == "NetworkAttachmentDefinition"
        }
        deployments = [document for document in documents if document.get("kind") == "Deployment"]

        self.assertEqual(nad_by_name["net-150-net0"]["type"], "bridge")
        self.assertEqual(nad_by_name["net-ix-ix100"]["type"], "macvlan")

        first_router = next(
            deployment for deployment in deployments
            if deployment["spec"]["template"]["metadata"]["labels"]["seedemu.io/asn"] == "150"
        )
        networks = json.loads(first_router["spec"]["template"]["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks"])
        by_name = {entry["name"]: entry for entry in networks}

        self.assertEqual(by_name["net-150-net0"], {"name": "net-150-net0"})
        self.assertIn("ips", by_name["net-ix-ix100"])


class PlacementHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helper_path = Path(__file__).resolve().parents[1] / "scripts" / "seed_k8s_verify_by_as_placement.py"
        spec = importlib.util.spec_from_file_location("seed_k8s_verify_by_as_placement", helper_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("failed to load placement helper")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.helper = module

    def test_helper_fails_when_same_asn_spans_multiple_nodes(self):
        pods_json = {
            "items": [
                {
                    "metadata": {"name": "as150-r0", "labels": {"seedemu.io/workload": "seedemu", "seedemu.io/asn": "150"}},
                    "spec": {"nodeName": "node-a"},
                },
                {
                    "metadata": {"name": "as150-h0", "labels": {"seedemu.io/workload": "seedemu", "seedemu.io/asn": "150"}},
                    "spec": {"nodeName": "node-b"},
                },
                {
                    "metadata": {"name": "as151-r0", "labels": {"seedemu.io/workload": "seedemu", "seedemu.io/asn": "151"}},
                    "spec": {"nodeName": "node-b"},
                },
            ]
        }
        nodes_json = {
            "items": [
                {"metadata": {"name": "node-a"}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}, "spec": {},},
                {"metadata": {"name": "node-b"}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}, "spec": {},},
            ]
        }

        def fake_check_output(cmd, text=True):
            if cmd[:4] == ["kubectl", "-n", "seedemu-test", "get"] and cmd[4] == "pods":
                return json.dumps(pods_json)
            if cmd[:3] == ["kubectl", "get", "nodes"]:
                return json.dumps(nodes_json)
            raise AssertionError(f"unexpected command: {cmd}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            expected_path = Path(tmp_dir) / "placement_expected.json"
            expected_path.write_text(json.dumps({"150": {"kubernetes.io/hostname": "node-a"}}), encoding="utf-8")
            argv = [
                "seed_k8s_verify_by_as_placement.py",
                "seedemu-test",
                tmp_dir,
                "by_as_hard",
                "2",
                str(expected_path),
            ]
            with mock.patch.object(self.helper.subprocess, "check_output", side_effect=fake_check_output), \
                 mock.patch.object(self.helper.sys, "argv", argv):
                rc = self.helper.main()

            self.assertEqual(rc, 1)
            check = json.loads((Path(tmp_dir) / "placement_check.json").read_text(encoding="utf-8"))
            self.assertEqual(check["failure_reason"], "asn_split_across_nodes")
            self.assertIn("ASN 150 spans multiple nodes", "\n".join(check["errors"]))


if __name__ == "__main__":
    unittest.main()
