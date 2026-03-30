import unittest
from pathlib import Path

import yaml


class SeedK8sProfileContractTest(unittest.TestCase):
    def test_official_profiles_define_validation_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        profiles_path = repo_root / "configs" / "seed_k8s_profiles.yaml"
        data = yaml.safe_load(profiles_path.read_text(encoding="utf-8")) or {}
        profiles = data.get("profiles", {}) if isinstance(data, dict) else {}

        required_minimal = {
            "summary.json",
            "placement_by_as.tsv",
            "protocol_health.json",
            "connectivity_matrix.tsv",
            "convergence_timeline.json",
            "failure_injection_summary.json",
            "resource_summary.json",
            "relationship_graph.json",
            "network_attachment_matrix.tsv",
        }

        expected_support = {
            "mini_internet": ("tier1", "runtime_strict"),
            "real_topology_rr": ("tier1", "runtime_strict"),
            "real_topology_rr_scale": ("tier1", "runtime_strict"),
            "transit_as": ("tier2", "runtime_capability_gated"),
            "mini_internet_viz": ("tier2", "runtime_capability_gated"),
            "hybrid_kubevirt": ("tier2", "runtime_capability_gated"),
        }

        for profile_id, (support_tier, acceptance_level) in expected_support.items():
            with self.subTest(profile_id=profile_id):
                profile = profiles.get(profile_id)
                self.assertIsInstance(profile, dict)
                assert isinstance(profile, dict)

                self.assertEqual(profile.get("profile_id"), profile_id)
                self.assertEqual(profile.get("support_tier"), support_tier)
                self.assertEqual(profile.get("acceptance_level"), acceptance_level)
                self.assertIn(profile.get("capacity_gate"), {"none", "reference_cluster_only", "large_hardware_required"})
                self.assertIn("default_topology_size", profile)
                self.assertIsInstance(profile.get("default_topology_size"), int)
                self.assertTrue(profile.get("compile_script"), "compile_script must be set")
                compile_script = repo_root / str(profile.get("compile_script"))
                self.assertTrue(compile_script.exists(), f"compile_script missing: {compile_script}")

                self.assertTrue(profile.get("default_namespace"), "default_namespace must be set")
                self.assertTrue(profile.get("default_cni_type"), "default_cni_type must be set")
                self.assertTrue(profile.get("default_scheduling_strategy"), "default_scheduling_strategy must be set")
                self.assertTrue(profile.get("verify_mode"), "verify_mode must be set")

                required_files = set(profile.get("validation_required_files", []) or [])
                missing = sorted(required_minimal - required_files)
                self.assertFalse(missing, f"validation_required_files missing: {missing}")


if __name__ == "__main__":
    unittest.main()
