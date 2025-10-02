import json
import sys
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import seed_network_helper as helper  # noqa: E402


class SeedNetworkHelperTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(helper, "_require_docker", return_value="/usr/bin/docker")
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_link_container_creates_network_and_connects(self):
        calls = []

        def fake_run(args, check=False):
            calls.append((tuple(args), check))
            if tuple(args[:2]) == ("network", "inspect"):
                # 模拟网络不存在
                return helper.DockerCommandResult(1, "", "not found")
            if tuple(args[:2]) == ("network", "create"):
                if check and False:
                    raise AssertionError("should not fail")
                return helper.DockerCommandResult(0, "created", "")
            if tuple(args[:2]) == ("inspect", "-f"):
                return helper.DockerCommandResult(0, json.dumps({}), "")
            if tuple(args[:2]) == ("network", "connect"):
                return helper.DockerCommandResult(0, "", "")
            raise AssertionError(f"unexpected docker call: {args}")

        with mock.patch.object(helper, "_run_docker", side_effect=fake_run):
            changed = helper.link_container_to_seed_network(
                "demo_container",
                network_name="seed_emulator",
                create_network=True,
                aliases=["gophish"],
            )
        self.assertTrue(changed)
        connect_calls = [call for call in calls if call[0][0:2] == ("network", "connect")]
        self.assertTrue(connect_calls)
        first_args = connect_calls[0][0]
        self.assertEqual(first_args[0:4], ("network", "connect", "seed_emulator", "demo_container"))
        self.assertIn("--alias", first_args)

    def test_link_container_noop_when_already_connected(self):
        def fake_run(args, check=False):
            if tuple(args[:2]) == ("network", "inspect"):
                return helper.DockerCommandResult(0, "details", "")
            if tuple(args[:2]) == ("inspect", "-f"):
                return helper.DockerCommandResult(0, json.dumps({"seed_emulator": {}}), "")
            raise AssertionError("unexpected call when container already connected")

        with mock.patch.object(helper, "_run_docker", side_effect=fake_run):
            changed = helper.link_container_to_seed_network("demo", create_network=False)

        self.assertFalse(changed)

    def test_disconnect_container(self):
        calls = []

        def fake_run(args, check=False):
            calls.append(tuple(args))
            if tuple(args[:2]) == ("inspect", "-f"):
                return helper.DockerCommandResult(0, json.dumps({"seed_emulator": {}}), "")
            if tuple(args[:2]) == ("network", "disconnect"):
                return helper.DockerCommandResult(0, "", "")
            raise AssertionError(f"unexpected call: {args}")

        with mock.patch.object(helper, "_run_docker", side_effect=fake_run):
            changed = helper.unlink_container_from_seed_network("demo")

        self.assertTrue(changed)
        self.assertIn(("network", "disconnect", "seed_emulator", "demo"), calls)

    def test_handle_cli_status(self):
        def fake_run(args, check=False):
            if tuple(args[:2]) == ("inspect", "-f"):
                return helper.DockerCommandResult(0, json.dumps({}), "")
            raise AssertionError(f"unexpected args: {args}")

        with mock.patch.object(helper, "_run_docker", side_effect=fake_run):
            exit_code = helper.handle_cli(["--network", "seed_emulator", "status", "demo"])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
