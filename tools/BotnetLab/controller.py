#!/usr/bin/env python3
"""Small dependency-free command-and-status controller for SEED botnet labs."""

from __future__ import annotations

import argparse
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import re
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse
import uuid


API_VERSION = 1
MAX_BODY_BYTES = 64 * 1024
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}


class ProtocolError(ValueError):
    """An invalid BotnetLab API request."""


def require_name(value: Any, field: str) -> str:
    text = str(value or "")
    if not NAME_PATTERN.fullmatch(text):
        raise ProtocolError(f"{field} contains unsupported characters or is too long")
    return text


def bounded_number(
    value: Any,
    field: str,
    minimum: float,
    maximum: float,
    default: float,
) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ProtocolError(f"{field} must be a number") from error
    if not minimum <= number <= maximum:
        raise ProtocolError(f"{field} must be between {minimum:g} and {maximum:g}")
    return number


class ControllerState:
    def __init__(
        self,
        offline_after: float = 10.0,
        delivery_lease: float = 15.0,
    ) -> None:
        self.offline_after = offline_after
        self.delivery_lease = delivery_lease
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.bots: dict[str, dict[str, Any]] = {}
        self.commands: dict[str, dict[str, Any]] = {}

    def register_bot(self, request: dict[str, Any], peer_address: str) -> dict[str, Any]:
        bot_id = require_name(request.get("bot_id"), "bot_id")
        hostname = require_name(request.get("hostname", bot_id), "hostname")
        capabilities_value = request.get("capabilities", [])
        if not isinstance(capabilities_value, list) or len(capabilities_value) > 64:
            raise ProtocolError("capabilities must be a list containing at most 64 names")
        capabilities = sorted(
            {require_name(item, "capability") for item in capabilities_value}
        )
        metadata = request.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ProtocolError("metadata must be an object")
        metadata = {str(key)[:64]: str(value)[:256] for key, value in metadata.items()}
        now = time.time()

        with self.changed:
            previous = self.bots.get(bot_id)
            bot = {
                "bot_id": bot_id,
                "hostname": hostname,
                "address": str(request.get("address") or peer_address)[:128],
                "peer_address": peer_address,
                "asn": str(request.get("asn", ""))[:32],
                "capabilities": capabilities,
                "metadata": metadata,
                "registered_at": previous["registered_at"] if previous else now,
                "last_seen": now,
                "agent_state": "idle",
                "current_command_id": None,
            }
            self.bots[bot_id] = bot
            self.changed.notify_all()
        return {
            "api_version": API_VERSION,
            "bot_id": bot_id,
            "registered": True,
            "server_time": now,
        }

    def heartbeat(self, request: dict[str, Any], peer_address: str) -> dict[str, Any]:
        bot_id = require_name(request.get("bot_id"), "bot_id")
        with self.changed:
            bot = self.bots.get(bot_id)
            if bot is None:
                raise KeyError(bot_id)
            bot["last_seen"] = time.time()
            bot["peer_address"] = peer_address
            bot["agent_state"] = str(request.get("agent_state", "idle"))[:32]
            command_id = request.get("current_command_id")
            bot["current_command_id"] = str(command_id)[:64] if command_id else None
            self.changed.notify_all()
        return {"status": "ok", "server_time": time.time()}

    def create_command(self, request: dict[str, Any]) -> dict[str, Any]:
        task_type = require_name(request.get("task_type"), "task_type")
        parameters = request.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ProtocolError("parameters must be an object")
        # Round-trip here also rejects values that cannot be represented as JSON.
        encoded_parameters = json.dumps(parameters, separators=(",", ":"))
        if len(encoded_parameters.encode("utf-8")) > 32 * 1024:
            raise ProtocolError("parameters are too large")

        start_delay = bounded_number(
            request.get("start_delay_seconds"),
            "start_delay_seconds",
            0,
            60,
            2,
        )
        timeout_seconds = bounded_number(
            request.get("timeout_seconds"),
            "timeout_seconds",
            1,
            300,
            60,
        )
        expires_in = bounded_number(
            request.get("expires_in_seconds"),
            "expires_in_seconds",
            5,
            3600,
            120,
        )
        requested_targets = request.get("targets", "all")
        now = time.time()

        with self.changed:
            if requested_targets == "all":
                target_ids = sorted(self.bots)
            elif isinstance(requested_targets, list):
                target_ids = [require_name(item, "target bot_id") for item in requested_targets]
                unknown = sorted(set(target_ids) - set(self.bots))
                if unknown:
                    raise ProtocolError("unknown target bots: {}".format(", ".join(unknown)))
                target_ids = sorted(set(target_ids))
            else:
                raise ProtocolError("targets must be 'all' or a list of bot IDs")

            capable = [
                bot_id
                for bot_id in target_ids
                if task_type in self.bots[bot_id]["capabilities"]
            ]
            command_id = uuid.uuid4().hex[:12]
            command = {
                "command_id": command_id,
                "task_type": task_type,
                "parameters": json.loads(encoded_parameters),
                "created_at": now,
                "start_at": now + start_delay,
                "expires_at": now + expires_in,
                "timeout_seconds": timeout_seconds,
                "cancelled": False,
                "requested_target_count": len(target_ids),
                "incapable_targets": sorted(set(target_ids) - set(capable)),
                "assignments": {
                    bot_id: {
                        "bot_id": bot_id,
                        "status": "pending",
                        "delivery_count": 0,
                        "delivered_at": None,
                        "lease_until": None,
                        "started_at": None,
                        "finished_at": None,
                        "result": None,
                    }
                    for bot_id in capable
                },
            }
            self.commands[command_id] = command
            self.changed.notify_all()
            return self._command_snapshot(command)

    def next_task(self, bot_id: str, wait_seconds: float) -> dict[str, Any] | None:
        bot_id = require_name(bot_id, "bot_id")
        wait_seconds = max(0.0, min(wait_seconds, 30.0))
        deadline = time.monotonic() + wait_seconds

        with self.changed:
            if bot_id not in self.bots:
                raise KeyError(bot_id)
            while True:
                now = time.time()
                self.bots[bot_id]["last_seen"] = now
                self._expire_assignments(now)
                for command in self.commands.values():
                    assignment = command["assignments"].get(bot_id)
                    if assignment is None or command["cancelled"]:
                        continue
                    deliverable = assignment["status"] == "pending" or (
                        assignment["status"] == "delivered"
                        and float(assignment["lease_until"] or 0) <= now
                    )
                    if not deliverable:
                        continue
                    assignment["status"] = "delivered"
                    assignment["delivery_count"] += 1
                    assignment["delivered_at"] = now
                    assignment["lease_until"] = now + self.delivery_lease
                    self.bots[bot_id]["agent_state"] = "assigned"
                    self.bots[bot_id]["current_command_id"] = command["command_id"]
                    return {
                        "command_id": command["command_id"],
                        "task_type": command["task_type"],
                        "parameters": command["parameters"],
                        "created_at": command["created_at"],
                        "start_at": command["start_at"],
                        "expires_at": command["expires_at"],
                        "timeout_seconds": command["timeout_seconds"],
                    }

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.changed.wait(min(remaining, 1.0))

    def report_status(
        self,
        command_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        command_id = require_name(command_id, "command_id")
        bot_id = require_name(request.get("bot_id"), "bot_id")
        status = str(request.get("status", ""))
        if status not in {"running", "completed", "failed"}:
            raise ProtocolError("status must be running, completed, or failed")
        result = request.get("result")
        if result is not None:
            encoded = json.dumps(result, separators=(",", ":"))
            if len(encoded.encode("utf-8")) > 32 * 1024:
                raise ProtocolError("result is too large")
            result = json.loads(encoded)
        now = time.time()

        with self.changed:
            command = self.commands.get(command_id)
            if command is None:
                raise KeyError(command_id)
            assignment = command["assignments"].get(bot_id)
            if assignment is None:
                raise ProtocolError("bot is not assigned to this command")
            if assignment["status"] in {"expired", "cancelled"}:
                raise ProtocolError(f"assignment is already {assignment['status']}")
            if status == "running":
                assignment["status"] = "running"
                assignment["started_at"] = assignment["started_at"] or now
                assignment["lease_until"] = None
                self.bots[bot_id]["agent_state"] = "running"
                self.bots[bot_id]["current_command_id"] = command_id
            else:
                assignment["status"] = status
                assignment["started_at"] = assignment["started_at"] or now
                assignment["finished_at"] = now
                assignment["lease_until"] = None
                assignment["result"] = result
                self.bots[bot_id]["agent_state"] = "idle"
                self.bots[bot_id]["current_command_id"] = None
            self.bots[bot_id]["last_seen"] = now
            self.changed.notify_all()
            return {"status": "accepted", "command_id": command_id, "bot_id": bot_id}

    def cancel_command(self, command_id: str) -> dict[str, Any]:
        command_id = require_name(command_id, "command_id")
        with self.changed:
            command = self.commands.get(command_id)
            if command is None:
                raise KeyError(command_id)
            command["cancelled"] = True
            now = time.time()
            for assignment in command["assignments"].values():
                if assignment["status"] in {"pending", "delivered"}:
                    assignment["status"] = "cancelled"
                    assignment["finished_at"] = now
                    assignment["lease_until"] = None
                    bot = self.bots.get(assignment["bot_id"])
                    if bot and bot["current_command_id"] == command_id:
                        bot["current_command_id"] = None
                        bot["agent_state"] = "idle"
            self.changed.notify_all()
            return self._command_snapshot(command)

    def reset_commands(self) -> dict[str, Any]:
        with self.changed:
            removed = len(self.commands)
            self.commands.clear()
            for bot in self.bots.values():
                bot["current_command_id"] = None
                if bot["agent_state"] != "offline":
                    bot["agent_state"] = "idle"
            self.changed.notify_all()
        return {"status": "reset", "commands_removed": removed}

    def bots_snapshot(self) -> dict[str, Any]:
        now = time.time()
        with self.lock:
            bots = []
            for stored in sorted(self.bots.values(), key=lambda item: item["bot_id"]):
                bot = dict(stored)
                bot["last_seen_age_seconds"] = round(max(0.0, now - bot["last_seen"]), 3)
                bot["online"] = bot["last_seen_age_seconds"] <= self.offline_after
                if not bot["online"]:
                    bot["agent_state"] = "offline"
                bots.append(bot)
            return {
                "api_version": API_VERSION,
                "server_time": now,
                "bot_count": len(bots),
                "online_count": sum(1 for bot in bots if bot["online"]),
                "bots": bots,
            }

    def commands_snapshot(self) -> dict[str, Any]:
        with self.lock:
            self._expire_assignments(time.time())
            commands = [self._command_snapshot(item) for item in self.commands.values()]
            commands.reverse()
            return {
                "api_version": API_VERSION,
                "command_count": len(commands),
                "commands": commands,
            }

    def command_snapshot(self, command_id: str) -> dict[str, Any]:
        with self.lock:
            self._expire_assignments(time.time())
            command = self.commands.get(command_id)
            if command is None:
                raise KeyError(command_id)
            return self._command_snapshot(command, include_assignments=True)

    def _expire_assignments(self, now: float) -> None:
        for command in self.commands.values():
            if now <= command["expires_at"]:
                continue
            for assignment in command["assignments"].values():
                if assignment["status"] in {"pending", "delivered"}:
                    assignment["status"] = "expired"
                    assignment["finished_at"] = now
                    assignment["lease_until"] = None

    def _command_snapshot(
        self,
        command: dict[str, Any],
        include_assignments: bool = False,
    ) -> dict[str, Any]:
        counts = Counter(item["status"] for item in command["assignments"].values())
        statuses = list(counts.elements())
        if command["cancelled"]:
            state = "cancelled"
        elif not statuses:
            state = "empty"
        elif all(status in TERMINAL_STATUSES for status in statuses):
            state = "completed"
        elif any(status == "running" for status in statuses):
            state = "running"
        elif any(status == "delivered" for status in statuses):
            state = "delivering"
        else:
            state = "pending"
        snapshot = {
            key: value
            for key, value in command.items()
            if key not in {"assignments", "cancelled"}
        }
        snapshot.update(
            {
                "state": state,
                "cancelled": command["cancelled"],
                "assignment_count": len(command["assignments"]),
                "status_counts": dict(sorted(counts.items())),
            }
        )
        if include_assignments:
            snapshot["assignments"] = [
                dict(command["assignments"][bot_id])
                for bot_id in sorted(command["assignments"])
            ]
        return snapshot


def make_handler(
    state: ControllerState,
    token: str,
    public_status: bool,
    cors_origin: str,
):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path == "/healthz":
                    self._send_json(200, {"status": "ok", "api_version": API_VERSION}, public=True)
                elif path == "/api/bots":
                    self._require_status_access()
                    self._send_json(200, state.bots_snapshot(), public=True)
                elif path == "/api/commands":
                    self._require_status_access()
                    self._send_json(200, state.commands_snapshot(), public=True)
                elif path.startswith("/api/commands/"):
                    self._require_status_access()
                    command_id = path.split("/")[3]
                    self._send_json(200, state.command_snapshot(command_id), public=True)
                elif path == "/api/tasks":
                    self._require_token()
                    query = parse_qs(parsed.query)
                    bot_id = query.get("bot_id", [""])[0]
                    wait_seconds = bounded_number(
                        query.get("wait", ["0"])[0], "wait", 0, 30, 0
                    )
                    task = state.next_task(bot_id, wait_seconds)
                    self._send_json(200, {"task": task, "server_time": time.time()})
                else:
                    self._send_json(404, {"error": "not found"})
            except KeyError as error:
                self._send_json(404, {"error": f"unknown identifier: {error.args[0]}"})
            except ProtocolError as error:
                self._send_json(400, {"error": str(error)})
            except PermissionError:
                pass

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                self._require_token()
                request = self._read_json()
                if path == "/api/register":
                    payload = state.register_bot(request, self.client_address[0])
                    self._send_json(200, payload)
                elif path == "/api/heartbeat":
                    payload = state.heartbeat(request, self.client_address[0])
                    self._send_json(200, payload)
                elif path == "/api/commands":
                    self._send_json(201, state.create_command(request))
                elif path == "/api/reset":
                    self._send_json(200, state.reset_commands())
                elif path.startswith("/api/commands/") and path.endswith("/cancel"):
                    command_id = path.split("/")[3]
                    self._send_json(200, state.cancel_command(command_id))
                elif path.startswith("/api/tasks/") and path.endswith("/status"):
                    command_id = path.split("/")[3]
                    self._send_json(200, state.report_status(command_id, request))
                else:
                    self._send_json(404, {"error": "not found"})
            except KeyError as error:
                self._send_json(404, {"error": f"unknown identifier: {error.args[0]}"})
            except (ProtocolError, json.JSONDecodeError) as error:
                self._send_json(400, {"error": str(error)})
            except PermissionError:
                pass

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()

        def _require_status_access(self) -> None:
            if not public_status:
                self._require_token()

        def _require_token(self) -> None:
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            if not hmac.compare_digest(supplied, expected):
                self._send_json(401, {"error": "unauthorized"})
                raise PermissionError

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ProtocolError("invalid Content-Length") from error
            if length < 0 or length > MAX_BODY_BYTES:
                raise ProtocolError("request body is too large")
            body = self.rfile.read(length)
            value = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(value, dict):
                raise ProtocolError("request body must be a JSON object")
            return value

        def _send_json(self, status: int, payload: dict[str, Any], public: bool = False) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if public:
                self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: Any) -> None:
            pass

    return Handler


def build_server(
    host: str,
    port: int,
    state: ControllerState,
    token: str,
    public_status: bool = True,
    cors_origin: str = "*",
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (host, port),
        make_handler(state, token, public_status, cors_origin),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SEED BotnetLab controller.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--token", default="seed-botnet-lab")
    parser.add_argument("--offline-after", type=float, default=10.0)
    parser.add_argument("--delivery-lease", type=float, default=15.0)
    parser.add_argument("--cors-origin", default="*")
    parser.add_argument(
        "--private-status",
        action="store_true",
        help="require the bearer token for read-only bot and command status APIs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        raise SystemExit("--token cannot be empty")
    state = ControllerState(
        offline_after=max(1.0, args.offline_after),
        delivery_lease=max(1.0, args.delivery_lease),
    )
    server = build_server(
        args.host,
        args.port,
        state,
        args.token,
        public_status=not args.private_status,
        cors_origin=args.cors_origin,
    )
    print(
        f"BotnetLab controller listening on http://{args.host}:{args.port} "
        f"(public_status={not args.private_status})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
