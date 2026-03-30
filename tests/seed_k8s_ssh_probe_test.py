#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "seed_k8s_ssh_probe.py"
    spec = importlib.util.spec_from_file_location("seed_k8s_ssh_probe", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SeedK8sSshProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_parse_node_spec_accepts_equals_and_colon(self) -> None:
        self.assertEqual(self.module.parse_node_spec("master=192.168.122.110"), ("master", "192.168.122.110"))
        self.assertEqual(self.module.parse_node_spec("worker1:192.168.122.111"), ("worker1", "192.168.122.111"))

    def test_collect_probe_summary_reports_success(self) -> None:
        completed = self.module.subprocess.CompletedProcess

        def fake_run(command, timeout):
            remote_command = command[-1]
            if remote_command == "hostname":
                return completed(command, 0, stdout="seed-k3s-master\n", stderr="")
            return completed(command, 0, stdout="", stderr="")

        with patch.object(self.module.Path, "is_file", return_value=True), patch.object(
            self.module, "run_remote_command", side_effect=fake_run
        ):
            summary = self.module.collect_probe_summary(
                "ubuntu",
                "~/.ssh/id_ed25519",
                8,
                [("seed-k3s-master", "192.168.122.110")],
            )

        self.assertTrue(summary["key_exists"])
        self.assertTrue(summary["ssh_access_ok"])
        self.assertTrue(summary["sudo_nopasswd_ok"])
        self.assertEqual(summary["nodes"][0]["hostname"], "seed-k3s-master")

    def test_collect_probe_summary_reports_missing_key(self) -> None:
        with patch.object(self.module.Path, "is_file", return_value=False):
            summary = self.module.collect_probe_summary(
                "ubuntu",
                "~/.ssh/missing",
                8,
                [("seed-k3s-master", "192.168.122.110")],
            )

        self.assertFalse(summary["key_exists"])
        self.assertFalse(summary["ssh_access_ok"])
        self.assertIn("key not found", summary["nodes"][0]["ssh_error"])


if __name__ == "__main__":
    unittest.main()
