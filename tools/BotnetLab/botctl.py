#!/usr/bin/env python3
"""Operator CLI for the SEED BotnetLab controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TERMINAL_STATES = {"completed", "cancelled", "empty"}


class ControlError(RuntimeError):
    pass


def request_json(
    controller: str,
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
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
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            message = json.loads(error.read().decode("utf-8")).get("error", str(error))
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = str(error)
        raise ControlError(message) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ControlError(str(error)) from error


def load_parameters(args: argparse.Namespace) -> dict[str, Any]:
    if args.parameters_file:
        text = Path(args.parameters_file).read_text(encoding="utf-8")
    else:
        text = args.parameters
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ControlError(f"invalid parameter JSON: {error}") from error
    if not isinstance(value, dict):
        raise ControlError("parameters must decode to a JSON object")
    return value


def print_bots(payload: dict[str, Any]) -> None:
    print(f"bots={payload['bot_count']} online={payload['online_count']}")
    print(
        f"{'BOT ID':<24} {'ONLINE':<7} {'STATE':<11} "
        f"{'ASN':<8} {'IP ADDRESS':<39} CAPABILITIES"
    )
    for bot in payload["bots"]:
        print(
            f"{bot['bot_id']:<24} "
            f"{('yes' if bot['online'] else 'no'):<7} "
            f"{bot['agent_state']:<11} "
            f"{bot['asn']:<8} "
            f"{bot['address'] or '-':<39} "
            f"{','.join(bot['capabilities']) or '-'}"
        )


def print_commands(payload: dict[str, Any]) -> None:
    print(f"commands={payload['command_count']}")
    print(f"{'COMMAND':<14} {'TASK':<18} {'STATE':<11} {'BOTS':<6} STATUS COUNTS")
    for command in payload["commands"]:
        counts = ",".join(
            f"{name}={count}" for name, count in command["status_counts"].items()
        )
        print(
            f"{command['command_id']:<14} {command['task_type']:<18} "
            f"{command['state']:<11} {command['assignment_count']:<6} {counts or '-'}"
        )


def print_command(payload: dict[str, Any]) -> None:
    print(
        f"command={payload['command_id']} task={payload['task_type']} "
        f"state={payload['state']} bots={payload['assignment_count']}"
    )
    print(f"status_counts={json.dumps(payload['status_counts'], sort_keys=True)}")
    if payload.get("incapable_targets"):
        print("incapable_targets={}".format(",".join(payload["incapable_targets"])))
    assignments = payload.get("assignments", [])
    if assignments:
        print(f"{'BOT ID':<24} {'STATUS':<11} {'DELIVERIES':<10} RESULT")
        for assignment in assignments:
            result = assignment.get("result")
            summary = "-" if result is None else json.dumps(result, separators=(",", ":"))
            if len(summary) > 100:
                summary = summary[:97] + "..."
            print(
                f"{assignment['bot_id']:<24} {assignment['status']:<11} "
                f"{assignment['delivery_count']:<10} {summary}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control a SEED BotnetLab controller.")
    parser.add_argument(
        "--controller",
        default=os.environ.get("BOTNETLAB_CONTROLLER", "http://127.0.0.1:8080"),
    )
    parser.add_argument("--token", default=os.environ.get("BOTNETLAB_TOKEN", "seed-botnet-lab"))
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("bots", help="list registered bots")
    subparsers.add_parser("commands", help="list commands")

    command = subparsers.add_parser("command", help="show one command")
    command.add_argument("command_id")
    command.add_argument("--watch", action="store_true")
    command.add_argument("--interval", type=float, default=1.0)

    launch = subparsers.add_parser("launch", help="broadcast an allowlisted task")
    launch.add_argument("task_type")
    launch.add_argument("--parameters", default="{}", help="JSON object")
    launch.add_argument("--parameters-file")
    launch.add_argument(
        "--targets",
        default="all",
        help="all, or a comma-separated list of bot IDs",
    )
    launch.add_argument("--start-delay", type=float, default=2.0)
    launch.add_argument("--timeout", type=float, default=60.0)
    launch.add_argument("--expires-in", type=float, default=120.0)

    cancel = subparsers.add_parser("cancel", help="cancel undelivered assignments")
    cancel.add_argument("command_id")
    subparsers.add_parser("reset", help="remove command history")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.token:
        parser.error("--token cannot be empty")
    try:
        if args.action == "bots":
            payload = request_json(args.controller, args.token, "GET", "/api/bots")
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print_bots(payload)
        elif args.action == "commands":
            payload = request_json(args.controller, args.token, "GET", "/api/commands")
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print_commands(payload)
        elif args.action == "command":
            while True:
                payload = request_json(
                    args.controller,
                    args.token,
                    "GET",
                    f"/api/commands/{args.command_id}",
                )
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print_command(payload)
                if not args.watch or payload["state"] in TERMINAL_STATES:
                    break
                time.sleep(max(0.2, args.interval))
                if not args.json:
                    print()
        elif args.action == "launch":
            targets: str | list[str]
            if args.targets == "all":
                targets = "all"
            else:
                targets = [item.strip() for item in args.targets.split(",") if item.strip()]
                if not targets:
                    raise ControlError("--targets must contain at least one bot ID")
            payload = request_json(
                args.controller,
                args.token,
                "POST",
                "/api/commands",
                {
                    "task_type": args.task_type,
                    "parameters": load_parameters(args),
                    "targets": targets,
                    "start_delay_seconds": args.start_delay,
                    "timeout_seconds": args.timeout,
                    "expires_in_seconds": args.expires_in,
                },
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print_command(payload)
        elif args.action == "cancel":
            payload = request_json(
                args.controller,
                args.token,
                "POST",
                f"/api/commands/{args.command_id}/cancel",
                {},
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print_command(payload)
        elif args.action == "reset":
            payload = request_json(args.controller, args.token, "POST", "/api/reset", {})
            print(json.dumps(payload, indent=2 if args.json else None, sort_keys=True))
    except (ControlError, OSError) as error:
        print(f"botctl: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
