#!/usr/bin/env python3

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "seed_k8s_bgp_health.py"
    spec = importlib.util.spec_from_file_location("seed_k8s_bgp_health", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load seed_k8s_bgp_health.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SeedK8sBgpHealthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def test_parse_bird_protocols_ignores_kubectl_noise(self):
        raw = """
I0317 09:45:09.528392 3553935 log.go:244] Create stream
BIRD 2.0.7 ready.
Name       Proto      Table      State  Since         Info
Ibgp_to_rr_r2 BGP        ---        up     09:31:41.022  Established
Ebgp_p_as1439 BGP        ---        start  09:31:41.022  Connect       Socket: No route to host
ospf1      OSPF       t_ospf     up     09:31:41.022  Running
"""
        rows = self.module.parse_bird_protocols(raw)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].family, "ibgp")
        self.assertTrue(rows[0].healthy)
        self.assertEqual(rows[1].family, "ebgp")
        self.assertFalse(rows[1].healthy)
        self.assertEqual(rows[2].family, "ospf")
        self.assertTrue(rows[2].healthy)

    def test_parse_bird_protocols_treats_ospf_alone_as_healthy(self):
        raw = """
BIRD 2.0.7 ready.
Name       Proto      Table      State  Since         Info
ospf1      OSPF       t_ospf     up     09:31:41.022  Alone
"""
        rows = self.module.parse_bird_protocols(raw)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].family, "ospf")
        self.assertTrue(rows[0].healthy)

    def test_determine_failure_reason_prioritizes_ibgp(self):
        summary = {
            "pods_checked": 3,
            "exec_failed_pods": [],
            "ibgp_total": 8,
            "ibgp_failed": 2,
            "ebgp_total": 4,
            "ebgp_failed": 0,
            "ospf_total": 4,
            "ospf_failed": 0,
        }
        self.assertEqual(self.module.determine_failure_reason(summary), "ibgp_incomplete")

    def test_determine_failure_reason_detects_ospf(self):
        summary = {
            "pods_checked": 2,
            "exec_failed_pods": [],
            "ibgp_total": 2,
            "ibgp_failed": 0,
            "ebgp_total": 1,
            "ebgp_failed": 0,
            "ospf_total": 2,
            "ospf_failed": 1,
        }
        self.assertEqual(self.module.determine_failure_reason(summary), "ospf_incomplete")

    def test_summarize_handles_no_ospf_rows(self):
        summary = self.module.summarize(
            "demo",
            [
                {
                    "pod": "router-a",
                    "exec_failed": False,
                    "ibgp_total": 1,
                    "ibgp_established": 1,
                    "ibgp_failed": 0,
                    "ebgp_total": 1,
                    "ebgp_established": 1,
                    "ebgp_failed": 0,
                    "ospf_total": 0,
                    "ospf_running": 0,
                    "ospf_failed": 0,
                }
            ],
        )
        self.assertEqual(summary["ospf_total"], 0)
        self.assertEqual(summary["ospf_running"], 0)
        self.assertEqual(summary["ospf_failed"], 0)
        self.assertEqual(summary["ospf_running_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
