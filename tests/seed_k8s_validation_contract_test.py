#!/usr/bin/env python3

import importlib.util
import json
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


class SeedK8sValidationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module("seed_k8s_validation_contract", "scripts/seed_k8s_validation_contract.py")

    def test_parse_bgp_neighbors_extracts_ibgp_and_ebgp(self):
        raw = """
protocol bgp Ibgp_to_rr_r13 {
  local as 1277;
  neighbor 10.0.0.1 as 1277;
}
protocol bgp Ebgp_p_as1439 {
  local as 1277;
  neighbor 10.0.0.2 as 1439;
}
"""
        rows = self.module._parse_bgp_neighbors(raw)
        self.assertEqual(rows[0]["family"], "ibgp")
        self.assertEqual(rows[0]["target_ip"], "10.0.0.1")
        self.assertEqual(rows[1]["family"], "ebgp")
        self.assertEqual(rows[1]["target_asn"], "1439")

    def test_assert_contract_writes_status_and_fails_on_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_dir = Path(tmp_dir)
            (artifact_dir / "summary.json").write_text("{}", encoding="utf-8")
            code = self.module.assert_contract(artifact_dir, ["summary.json", "resource_summary.json"])
            self.assertEqual(code, 1)
            status = json.loads((artifact_dir / "artifact_contract.json").read_text(encoding="utf-8"))
            self.assertIn("resource_summary.json", status["missing_files"])

    def test_derive_duration_fields_prefers_stage_sum_when_runner_shorter(self):
        durations = self.module._derive_duration_fields(
            {"duration_seconds": 99, "validation_duration_seconds": 17},
            {
                "build_duration_seconds": 420,
                "up_duration_seconds": 139,
                "phase_start_duration_seconds": 112,
            },
            {"duration_seconds": 20},
        )
        self.assertEqual(durations["validation_duration_seconds"], 17)
        self.assertEqual(durations["pipeline_duration_seconds"], 688)

    def test_required_files_for_profile_reads_extended_contract(self):
        repo_root = Path(__file__).resolve().parents[1]
        required = self.module.required_files_for_profile(
            repo_root / "configs" / "seed_k8s_profiles.yaml",
            "mini_internet",
        )
        self.assertIn("relationship_graph.json", required)
        self.assertIn("network_attachment_matrix.tsv", required)

    def test_write_convergence_timeline_records_pipeline_duration(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run"
            artifact_dir = run_dir / "validation"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "summary.json").write_text(
                json.dumps({"namespace": "demo", "duration_seconds": 15}),
                encoding="utf-8",
            )
            (artifact_dir / "timing.json").write_text(
                json.dumps(
                    {
                        "build_duration_seconds": 10,
                        "up_duration_seconds": 20,
                        "phase_start_duration_seconds": 30,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "runner_summary.json").write_text(json.dumps({"duration_seconds": 40}), encoding="utf-8")

            self.module._write_convergence_timeline(artifact_dir, "demo_profile")
            timeline = json.loads((artifact_dir / "convergence_timeline.json").read_text(encoding="utf-8"))

        self.assertEqual(timeline["validation_duration_seconds"], 15)
        self.assertEqual(timeline["pipeline_duration_seconds"], 75)
        self.assertEqual(timeline["duration_seconds"], 75)
