#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


class SeedK8sRunnerStageContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def test_runner_help_lists_staged_public_actions(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/seed_k8s_profile_runner.sh", "mini_internet", "help"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for action in (
            "compile",
            "build",
            "deploy",
            "start",
            "start-bird",
            "start-kernel",
            "phase-start",
            "verify",
            "observe",
            "report",
            "all",
        ):
            with self.subTest(action=action):
                self.assertIn(action, result.stdout)

    def test_staged_shortcuts_exist(self) -> None:
        shortcut_expectations = {
            "k3scompile": " compile",
            "k3sbuild": " build",
            "k3sdeploy": " deploy",
            "k3sup": " deploy",
            "k3sstartbird": " start-bird",
            "k3skernel": " start-kernel",
            "k3sphase": " phase-start",
        }
        for shortcut, expected_action in shortcut_expectations.items():
            path = self.repo_root / "scripts" / "shortcuts" / shortcut
            with self.subTest(shortcut=shortcut):
                self.assertTrue(path.exists(), f"missing shortcut: {shortcut}")
                text = path.read_text(encoding="utf-8")
                self.assertIn(expected_action, text)

    def test_start_stage_scripts_emit_canonical_artifacts(self) -> None:
        bird_script = (self.repo_root / "scripts" / "seed_k8s_start_bird0130.py").read_text(encoding="utf-8")
        kernel_script = (self.repo_root / "scripts" / "seed_k8s_start_bird_kernel.py").read_text(encoding="utf-8")

        self.assertIn("start_bird_summary.json", bird_script)
        self.assertIn("start_bird.log", bird_script)
        self.assertIn("bird0130_summary.json", bird_script)
        self.assertIn("bird0130.log", bird_script)

        self.assertIn("start_kernel_summary.json", kernel_script)
        self.assertIn("start_kernel.log", kernel_script)
        self.assertIn("bird_kernel_summary.json", kernel_script)
        self.assertIn("bird_kernel.log", kernel_script)


if __name__ == "__main__":
    unittest.main()
