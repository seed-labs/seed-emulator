#!/usr/bin/env python3

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module(name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SeedK8sRealTopologyPlannerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module("seed_k8s_plan_real_topology_by_as", "scripts/seed_k8s_plan_real_topology_by_as.py")

    def test_ready_nodes_subtracts_existing_pods_outside_target_namespace(self):
        nodes_payload = {
            "items": [
                {
                    "metadata": {
                        "name": "seed-k3s-master",
                        "labels": {"node-role.kubernetes.io/control-plane": "true"},
                    },
                    "spec": {},
                    "status": {
                        "allocatable": {"pods": "110"},
                        "conditions": [{"type": "Ready", "status": "True"}],
                    },
                },
                {
                    "metadata": {"name": "seed-k3s-worker2", "labels": {}},
                    "spec": {},
                    "status": {
                        "allocatable": {"pods": "110"},
                        "conditions": [{"type": "Ready", "status": "True"}],
                    },
                },
            ]
        }
        pods_payload = {
            "items": [
                {"metadata": {"namespace": "kube-system"}, "spec": {"nodeName": "seed-k3s-master"}},
                {"metadata": {"namespace": "kube-system"}, "spec": {"nodeName": "seed-k3s-master"}},
                {"metadata": {"namespace": "target-ns"}, "spec": {"nodeName": "seed-k3s-master"}},
                {"metadata": {"namespace": "kube-system"}, "spec": {"nodeName": "seed-k3s-worker2"}},
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            nodes_path = Path(tmp_dir) / "nodes.json"
            pods_path = Path(tmp_dir) / "pods.json"
            nodes_path.write_text(json.dumps(nodes_payload), encoding="utf-8")
            pods_path.write_text(json.dumps(pods_payload), encoding="utf-8")

            old_namespace = os.environ.get("SEED_NAMESPACE")
            try:
                os.environ["SEED_NAMESPACE"] = "target-ns"
                nodes = self.module.ready_nodes(nodes_path, pod_reserve=5, pods_json=pods_path)
            finally:
                if old_namespace is None:
                    os.environ.pop("SEED_NAMESPACE", None)
                else:
                    os.environ["SEED_NAMESPACE"] = old_namespace

        by_name = {item["name"]: item for item in nodes}
        self.assertEqual(by_name["seed-k3s-master"]["current_pods"], 2)
        self.assertEqual(by_name["seed-k3s-master"]["effective_capacity"], 103)
        self.assertEqual(by_name["seed-k3s-worker2"]["current_pods"], 1)
        self.assertEqual(by_name["seed-k3s-worker2"]["effective_capacity"], 104)

    def test_assign_prefers_node_with_more_real_remaining_capacity(self):
        nodes = [
            {
                "name": "seed-k3s-master",
                "effective_capacity": 80,
                "assigned_pods": 0,
                "assigned_asns": [],
                "is_control_plane": True,
            },
            {
                "name": "seed-k3s-worker1",
                "effective_capacity": 82,
                "assigned_pods": 0,
                "assigned_asns": [],
                "is_control_plane": False,
            },
            {
                "name": "seed-k3s-worker2",
                "effective_capacity": 89,
                "assigned_pods": 0,
                "assigned_asns": [],
                "is_control_plane": False,
            },
        ]

        mapping, plan = self.module.assign({"1277": 85, "1439": 25, "2010": 7}, nodes)

        self.assertEqual(mapping["1277"]["kubernetes.io/hostname"], "seed-k3s-worker2")
        self.assertIn("1277", plan["nodes"][2]["assigned_asns"])

    def test_assign_keeps_multi_pod_as_off_control_plane_when_worker_can_fit(self):
        nodes = [
            {
                "name": "seed-k3s-master",
                "effective_capacity": 101,
                "assigned_pods": 0,
                "assigned_asns": [],
                "is_control_plane": True,
            },
            {
                "name": "seed-k3s-worker1",
                "effective_capacity": 104,
                "assigned_pods": 86,
                "assigned_asns": ["1277"],
                "is_control_plane": False,
            },
            {
                "name": "seed-k3s-worker2",
                "effective_capacity": 104,
                "assigned_pods": 25,
                "assigned_asns": ["1439"],
                "is_control_plane": False,
            },
        ]

        mapping, plan = self.module.assign({"2010": 7, "2": 1, "3": 1}, nodes)

        self.assertEqual(mapping["2010"]["kubernetes.io/hostname"], "seed-k3s-worker2")
        self.assertIn("2010", plan["nodes"][2]["assigned_asns"])
        self.assertEqual(mapping["2"]["kubernetes.io/hostname"], "seed-k3s-master")
        self.assertEqual(mapping["3"]["kubernetes.io/hostname"], "seed-k3s-master")

    def test_validator_exports_namespace_when_recomputing_live_plan(self):
        validator_script = (
            Path(__file__).resolve().parents[1] / "scripts" / "validate_k3s_real_topology_multinode.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('SEED_NAMESPACE="${SEED_NAMESPACE}"', validator_script)
        self.assertIn('SEED_EXCLUDED_NAMESPACES="${SEED_NAMESPACE}"', validator_script)


if __name__ == "__main__":
    unittest.main()
