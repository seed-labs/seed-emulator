#!/usr/bin/env python3

import importlib.util
import sys
import tempfile
import textwrap
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


class SeedK8sClusterInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module("seed_k8s_cluster_inventory", "scripts/seed_k8s_cluster_inventory.py")

    def test_normalize_inventory_derives_registry_and_nodes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "cluster.yaml"
            path.write_text(
                textwrap.dedent(
                    """
                    cluster_name: demo
                    max_validated_topology_size: 1897
                    ssh:
                      user: tester
                      default_key_path: ~/.ssh/demo
                    registry:
                      host: 10.0.0.10
                      port: 5001
                    cni:
                      default_master_interface: ens2
                    k3s:
                      cluster_cidr: 10.42.0.0/16
                      service_cidr: 10.43.0.0/16
                      node_cidr_mask_size_ipv4: 22
                      max_pods: 700
                    nodes:
                      - name: demo-master
                        role: master
                        management_ip: 10.0.0.10
                      - name: demo-worker1
                        role: worker
                        management_ip: 10.0.0.11
                      - name: demo-worker2
                        role: worker
                        management_ip: 10.0.0.12
                    """
                ),
                encoding="utf-8",
            )
            normalized = self.module.normalize_inventory(path)

        self.assertEqual(normalized["cluster_name"], "demo")
        self.assertEqual(normalized["max_validated_topology_size"], 1897)
        self.assertEqual(normalized["registry_host"], "10.0.0.10")
        self.assertEqual(normalized["registry_port"], 5001)
        self.assertEqual(normalized["master_name"], "demo-master")
        self.assertEqual(normalized["worker1_ip"], "10.0.0.11")
        self.assertEqual(normalized["default_master_interface"], "ens2")
        self.assertEqual(normalized["k3s_cluster_cidr"], "10.42.0.0/16")
        self.assertEqual(normalized["k3s_service_cidr"], "10.43.0.0/16")
        self.assertEqual(normalized["k3s_node_cidr_mask_size_ipv4"], 22)
        self.assertEqual(normalized["k3s_max_pods"], 700)
