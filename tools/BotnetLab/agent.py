#!/usr/bin/env python3
"""Allowlisted task agent for the SEED BotnetLab controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


HANDLER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
MAX_CAPTURE_CHARS = 16 * 1024


class APIError(RuntimeError):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


def api_request(
    controller: str,
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        controller.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            message = json.loads(error.read().decode("utf-8")).get("error", str(error))
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = str(error)
        raise APIError(error.code, message) from error
    except (URLError, TimeoutError, OSError) as error:
        raise APIError(None, str(error)) from error


def parse_mapping(value: str, field: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"{field} must use NAME=VALUE syntax")
    name, item = value.split("=", 1)
    if not HANDLER_PATTERN.fullmatch(name):
        raise argparse.ArgumentTypeError(f"invalid {field} name: {name}")
    if not item:
        raise argparse.ArgumentTypeError(f"{field} value cannot be empty")
    return name, item


def handler_command(path: str) -> list[str]:
    resolved = Path(path).resolve()
    if resolved.suffix == ".py":
        return [sys.executable, str(resolved)]
    return [str(resolved)]


class BotAgent:
    def __init__(
        self,
        controller: str,
        token: str,
        bot_id: str,
        handlers: dict[str, str],
        hostname: str,
        address: str,
        asn: str,
        metadata: dict[str, str],
        heartbeat_interval: float = 2.0,
        poll_wait: float = 10.0,
        retry_interval: float = 2.0,
        max_task_seconds: float = 90.0,
    ) -> None:
        self.controller = controller.rstrip("/")
        self.token = token
        self.bot_id = bot_id
        self.handlers = handlers
        self.hostname = hostname
        self.address = address
        self.asn = asn
        self.metadata = metadata
        self.heartbeat_interval = max(0.5, heartbeat_interval)
        self.poll_wait = max(0.0, min(poll_wait, 30.0))
        self.retry_interval = max(0.2, retry_interval)
        self.max_task_seconds = max(1.0, max_task_seconds)
        self.stop_event = threading.Event()
        self.state_lock = threading.Lock()
        self.agent_state = "starting"
        self.current_command_id: str | None = None

    def registration(self) -> dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "hostname": self.hostname,
            "address": self.address,
            "asn": self.asn,
            "capabilities": sorted(self.handlers),
            "metadata": self.metadata,
        }

    def register_until_ready(self) -> None:
        while not self.stop_event.is_set():
            try:
                api_request(
                    self.controller,
                    self.token,
                    "POST",
                    "/api/register",
                    self.registration(),
                )
                self._set_state("idle", None)
                print(
                    f"BotnetLab agent {self.bot_id} registered with {self.controller} "
                    f"capabilities={','.join(sorted(self.handlers)) or '-'}",
                    flush=True,
                )
                return
            except APIError as error:
                print(f"registration failed: {error}; retrying", flush=True)
                self.stop_event.wait(self.retry_interval)

    def heartbeat_loop(self) -> None:
        while not self.stop_event.wait(self.heartbeat_interval):
            with self.state_lock:
                payload = {
                    "bot_id": self.bot_id,
                    "agent_state": self.agent_state,
                    "current_command_id": self.current_command_id,
                }
            try:
                api_request(
                    self.controller,
                    self.token,
                    "POST",
                    "/api/heartbeat",
                    payload,
                    timeout=max(2.0, self.heartbeat_interval),
                )
            except APIError as error:
                if error.status == 404:
                    try:
                        api_request(
                            self.controller,
                            self.token,
                            "POST",
                            "/api/register",
                            self.registration(),
                        )
                    except APIError:
                        pass

    def run(self) -> int:
        self.register_until_ready()
        if self.stop_event.is_set():
            return 0
        heartbeat = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat.start()

        while not self.stop_event.is_set():
            query = urlencode({"bot_id": self.bot_id, "wait": self.poll_wait})
            try:
                response = api_request(
                    self.controller,
                    self.token,
                    "GET",
                    f"/api/tasks?{query}",
                    timeout=self.poll_wait + 5.0,
                )
            except APIError as error:
                if error.status == 404:
                    self.register_until_ready()
                else:
                    print(f"task polling failed: {error}", flush=True)
                    self.stop_event.wait(self.retry_interval)
                continue

            task = response.get("task")
            if task is None:
                continue
            self.execute_task(task)
        return 0

    def execute_task(self, task: dict[str, Any]) -> None:
        command_id = str(task.get("command_id", ""))
        task_type = str(task.get("task_type", ""))
        handler = self.handlers.get(task_type)
        if not command_id or handler is None:
            if command_id:
                self._report(
                    command_id,
                    "failed",
                    {"error": f"unsupported task type: {task_type}"},
                )
            return

        now = time.time()
        expires_at = float(task.get("expires_at", now))
        if now >= expires_at:
            self._report(command_id, "failed", {"error": "task expired before execution"})
            return
        start_at = min(float(task.get("start_at", now)), expires_at)
        if start_at > now and self.stop_event.wait(start_at - now):
            return
        if time.time() >= expires_at:
            self._report(command_id, "failed", {"error": "task expired before execution"})
            return
        try:
            command = api_request(
                self.controller,
                self.token,
                "GET",
                f"/api/commands/{command_id}",
            )
            if command.get("cancelled"):
                self._set_state("idle", None)
                print(f"command {command_id}: cancelled before execution", flush=True)
                return
        except APIError as error:
            self._set_state("idle", None)
            print(
                f"command {command_id}: cancellation check failed, deferring execution: {error}",
                flush=True,
            )
            self.stop_event.wait(self.retry_interval)
            return

        self._set_state("running", command_id)
        if not self._report(command_id, "running"):
            self._set_state("idle", None)
            print(f"command {command_id}: not acknowledged; execution deferred", flush=True)
            return
        print(f"command {command_id}: starting {task_type}", flush=True)
        requested_timeout = float(task.get("timeout_seconds", self.max_task_seconds))
        timeout = max(1.0, min(requested_timeout, self.max_task_seconds))
        task_input = json.dumps(task, separators=(",", ":"))
        environment = os.environ.copy()
        environment.update(
            {
                "BOTNETLAB_BOT_ID": self.bot_id,
                "BOTNETLAB_COMMAND_ID": command_id,
                "BOTNETLAB_TASK_TYPE": task_type,
            }
        )
        started = time.monotonic()

        try:
            process = subprocess.Popen(
                handler_command(handler),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            try:
                stdout, stderr = process.communicate(task_input, timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                timed_out = True
            result = {
                "exit_code": process.returncode,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "stdout": stdout[-MAX_CAPTURE_CHARS:],
                "stderr": stderr[-MAX_CAPTURE_CHARS:],
                "timed_out": timed_out,
            }
            status = "completed" if process.returncode == 0 and not timed_out else "failed"
        except OSError as error:
            status = "failed"
            result = {
                "error": str(error),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }

        self._report(command_id, status, result)
        self._set_state("idle", None)
        print(
            f"command {command_id}: {status} in {result['elapsed_seconds']:.3f}s",
            flush=True,
        )

    def _report(
        self,
        command_id: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> bool:
        payload: dict[str, Any] = {"bot_id": self.bot_id, "status": status}
        if result is not None:
            payload["result"] = result
        while not self.stop_event.is_set():
            try:
                api_request(
                    self.controller,
                    self.token,
                    "POST",
                    f"/api/tasks/{command_id}/status",
                    payload,
                )
                return True
            except APIError as error:
                if error.status in {400, 401, 404}:
                    print(
                        f"command {command_id}: status report rejected: {error}",
                        flush=True,
                    )
                    return False
                print(f"command {command_id}: status report failed: {error}; retrying", flush=True)
                self.stop_event.wait(self.retry_interval)
        return False

    def _set_state(self, state: str, command_id: str | None) -> None:
        with self.state_lock:
            self.agent_state = state
            self.current_command_id = command_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an allowlisted SEED BotnetLab agent.")
    parser.add_argument("--controller", required=True, help="controller base URL")
    parser.add_argument("--token", default=os.environ.get("BOTNETLAB_TOKEN", "seed-botnet-lab"))
    parser.add_argument("--bot-id", default=socket.gethostname())
    parser.add_argument("--hostname", default=socket.gethostname())
    parser.add_argument("--address", default="")
    parser.add_argument("--asn", default="")
    parser.add_argument(
        "--handler",
        action="append",
        default=[],
        metavar="TASK=PATH",
        help="allow a task type and map it to a fixed executable handler",
    )
    parser.add_argument("--metadata", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--heartbeat-interval", type=float, default=2.0)
    parser.add_argument("--poll-wait", type=float, default=10.0)
    parser.add_argument("--retry-interval", type=float, default=2.0)
    parser.add_argument("--max-task-seconds", type=float, default=90.0)
    args = parser.parse_args()
    try:
        args.handlers = dict(parse_mapping(value, "handler") for value in args.handler)
        args.metadata_values = dict(parse_mapping(value, "metadata") for value in args.metadata)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))
    if not HANDLER_PATTERN.fullmatch(args.bot_id):
        parser.error("--bot-id contains unsupported characters or is too long")
    if not args.handlers:
        parser.error("at least one --handler is required")
    for path in args.handlers.values():
        if not Path(path).is_file():
            parser.error(f"handler does not exist: {path}")
    if not args.token:
        parser.error("--token cannot be empty")
    return args


def main() -> int:
    args = parse_args()
    agent = BotAgent(
        controller=args.controller,
        token=args.token,
        bot_id=args.bot_id,
        handlers=args.handlers,
        hostname=args.hostname,
        address=args.address,
        asn=args.asn,
        metadata=args.metadata_values,
        heartbeat_interval=args.heartbeat_interval,
        poll_wait=args.poll_wait,
        retry_interval=args.retry_interval,
        max_task_seconds=args.max_task_seconds,
    )

    def stop(_signum: int, _frame: Any) -> None:
        agent.stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return agent.run()


if __name__ == "__main__":
    raise SystemExit(main())
