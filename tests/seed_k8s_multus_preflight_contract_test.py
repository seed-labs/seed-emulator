import unittest
from pathlib import Path


class SeedK8sMultusPreflightContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def test_long_probe_timeout_exists_in_both_validators(self) -> None:
        expected_snippets = (
            'SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS="${SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS:-90}"',
            'run_ssh_probe_with_timeout "${SEED_SSH_LONG_PROBE_TIMEOUT_SECONDS}"',
            "multus.kubeconfig",
        )
        for script_name in (
            "scripts/validate_k3s_real_topology_multinode.sh",
            "scripts/validate_k3s_mini_internet_multinode.sh",
        ):
            with self.subTest(script=script_name):
                text = (self.repo_root / script_name).read_text(encoding="utf-8")
                for snippet in expected_snippets:
                    self.assertIn(snippet, text)


if __name__ == "__main__":
    unittest.main()
