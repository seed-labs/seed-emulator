#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from agent import BotAgent, api_request
from controller import ControllerState, ProtocolError, build_server


TOKEN = "test-token"


class ControllerStateTests(unittest.TestCase):
    def test_capabilities_limit_broadcast_assignments(self) -> None:
        state = ControllerState()
        state.register_bot(
            {
                "bot_id": "bot-1",
                "hostname": "bot-1",
                "capabilities": ["demo"],
            },
            "127.0.0.1",
        )
        state.register_bot(
            {
                "bot_id": "bot-2",
                "hostname": "bot-2",
                "capabilities": ["different-task"],
            },
            "127.0.0.1",
        )

        command = state.create_command(
            {
                "task_type": "demo",
                "parameters": {"message": "test"},
                "targets": "all",
            }
        )
        self.assertEqual(command["assignment_count"], 1)
        self.assertEqual(command["incapable_targets"], ["bot-2"])

    def test_invalid_target_is_rejected(self) -> None:
        state = ControllerState()
        with self.assertRaises(ProtocolError):
            state.create_command(
                {"task_type": "demo", "targets": ["not-registered"]}
            )


class HTTPIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = ControllerState(offline_after=2, delivery_lease=1)
        self.server = build_server("127.0.0.1", 0, self.state, TOKEN)
        self.server_url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)

    def test_authenticated_command_lifecycle(self) -> None:
        api_request(
            self.server_url,
            TOKEN,
            "POST",
            "/api/register",
            {
                "bot_id": "bot-http",
                "hostname": "bot-http",
                "capabilities": ["demo"],
            },
        )
        command = api_request(
            self.server_url,
            TOKEN,
            "POST",
            "/api/commands",
            {
                "task_type": "demo",
                "parameters": {"message": "hello"},
                "start_delay_seconds": 0,
            },
        )
        command_id = command["command_id"]
        response = api_request(
            self.server_url,
            TOKEN,
            "GET",
            "/api/tasks?bot_id=bot-http&wait=0",
        )
        self.assertEqual(response["task"]["command_id"], command_id)
        api_request(
            self.server_url,
            TOKEN,
            "POST",
            f"/api/tasks/{command_id}/status",
            {"bot_id": "bot-http", "status": "running"},
        )
        api_request(
            self.server_url,
            TOKEN,
            "POST",
            f"/api/tasks/{command_id}/status",
            {
                "bot_id": "bot-http",
                "status": "completed",
                "result": {"packets": 3},
            },
        )
        snapshot = api_request(
            self.server_url,
            TOKEN,
            "GET",
            f"/api/commands/{command_id}",
        )
        self.assertEqual(snapshot["state"], "completed")
        self.assertEqual(snapshot["status_counts"], {"completed": 1})
        self.assertEqual(snapshot["assignments"][0]["result"], {"packets": 3})

    def test_mutating_endpoint_requires_token(self) -> None:
        request = Request(
            self.server_url + "/api/register",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=2)
        self.assertEqual(context.exception.code, 401)

    def test_botctl_lists_bots_and_creates_command(self) -> None:
        api_request(
            self.server_url,
            TOKEN,
            "POST",
            "/api/register",
            {
                "bot_id": "bot-cli",
                "hostname": "bot-cli",
                "address": "10.152.0.73",
                "asn": "152",
                "capabilities": ["demo"],
            },
        )
        base_command = [
            sys.executable,
            str(SCRIPT_DIR / "botctl.py"),
            "--controller",
            self.server_url,
            "--token",
            TOKEN,
        ]
        listed = subprocess.run(
            base_command + ["bots"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("bot-cli", listed.stdout)
        self.assertIn("IP ADDRESS", listed.stdout)
        self.assertIn("10.152.0.73", listed.stdout)
        launched = subprocess.run(
            base_command
            + [
                "--json",
                "launch",
                "demo",
                "--parameters",
                '{"message":"from botctl"}',
                "--start-delay",
                "0",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        command = json.loads(launched.stdout)
        self.assertEqual(command["task_type"], "demo")
        self.assertEqual(command["assignment_count"], 1)

    def test_real_agent_executes_fixed_handler(self) -> None:
        agent = BotAgent(
            controller=self.server_url,
            token=TOKEN,
            bot_id="bot-agent",
            handlers={"demo": str(SCRIPT_DIR / "example_handler.py")},
            hostname="bot-agent",
            address="10.0.0.2",
            asn="65001",
            metadata={"role": "test"},
            heartbeat_interval=0.1,
            poll_wait=0.1,
            retry_interval=0.1,
            max_task_seconds=5,
        )
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        deadline = time.time() + 3
        while "bot-agent" not in self.state.bots and time.time() < deadline:
            time.sleep(0.02)
        self.assertIn("bot-agent", self.state.bots)

        command = self.state.create_command(
            {
                "task_type": "demo",
                "parameters": {"message": "integration", "delay_seconds": 0.01},
                "start_delay_seconds": 0,
                "timeout_seconds": 3,
            }
        )
        command_id = command["command_id"]
        deadline = time.time() + 5
        snapshot = self.state.command_snapshot(command_id)
        while snapshot["state"] != "completed" and time.time() < deadline:
            time.sleep(0.05)
            snapshot = self.state.command_snapshot(command_id)

        agent.stop_event.set()
        agent_thread.join(timeout=2)
        self.assertEqual(snapshot["state"], "completed")
        result = snapshot["assignments"][0]["result"]
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("integration", result["stdout"])

    def test_agent_honors_cancellation_before_scheduled_start(self) -> None:
        agent = BotAgent(
            controller=self.server_url,
            token=TOKEN,
            bot_id="bot-cancel",
            handlers={"demo": str(SCRIPT_DIR / "example_handler.py")},
            hostname="bot-cancel",
            address="10.0.0.3",
            asn="65002",
            metadata={},
            heartbeat_interval=0.1,
            poll_wait=0.05,
            retry_interval=0.1,
            max_task_seconds=5,
        )
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        deadline = time.time() + 3
        while "bot-cancel" not in self.state.bots and time.time() < deadline:
            time.sleep(0.02)

        command = self.state.create_command(
            {
                "task_type": "demo",
                "parameters": {"message": "must not run"},
                "start_delay_seconds": 0.5,
            }
        )
        command_id = command["command_id"]
        deadline = time.time() + 2
        snapshot = self.state.command_snapshot(command_id)
        while snapshot["status_counts"].get("delivered") != 1 and time.time() < deadline:
            time.sleep(0.02)
            snapshot = self.state.command_snapshot(command_id)
        self.assertEqual(snapshot["status_counts"], {"delivered": 1})
        self.state.cancel_command(command_id)
        time.sleep(0.7)
        snapshot = self.state.command_snapshot(command_id)

        agent.stop_event.set()
        agent_thread.join(timeout=2)
        self.assertEqual(snapshot["state"], "cancelled")
        self.assertEqual(snapshot["status_counts"], {"cancelled": 1})
        self.assertIsNone(snapshot["assignments"][0]["result"])


if __name__ == "__main__":
    unittest.main()
