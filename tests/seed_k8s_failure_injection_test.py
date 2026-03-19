#!/usr/bin/env python3

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


def _load_module(name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SeedK8sFailureInjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module("seed_k8s_failure_injection", "scripts/seed_k8s_failure_injection.py")

    def test_pick_target_prefers_router_pod_and_skips_ix(self):
        pod_json = {
            "items": [
                {
                    "metadata": {
                        "name": "as2brd-ix2-1.2.0.2-abc",
                        "labels": {
                            "seedemu.io/workload": "seedemu",
                            "seedemu.io/role": "brd",
                            "seedemu.io/name": "ix2",
                            "seedemu.io/asn": "2",
                            "app": "as2brd-ix2-1.2.0.2",
                        },
                    },
                    "status": {"phase": "Running"},
                },
                {
                    "metadata": {
                        "name": "as1277brd-r10-1.10.4.253-xyz",
                        "labels": {
                            "seedemu.io/workload": "seedemu",
                            "seedemu.io/role": "brd",
                            "seedemu.io/name": "r10",
                            "seedemu.io/asn": "1277",
                            "app": "as1277brd-r10-1.10.4.253",
                        },
                    },
                    "status": {"phase": "Running"},
                },
            ]
        }

        with mock.patch.object(self.module, "_kubectl_json", return_value=pod_json):
            target = self.module._pick_target("demo")

        self.assertIsNotNone(target)
        self.assertEqual(target["pod"], "as1277brd-r10-1.10.4.253-xyz")
        self.assertEqual(target["logical_name"], "r10")

