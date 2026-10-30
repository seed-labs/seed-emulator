#!/usr/bin/env python3
"""Bounded UDP sender for the Y13 SEED Emulator botnet lab."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from typing import Any


VICTIM_IP = "10.151.0.71"
VICTIM_PORT = 9000
MAX_DURATION = 60.0
MAX_PACKETS_PER_SECOND = 2000
MAX_PACKET_SIZE = 1400
MAX_ROUNDS = 20
MAX_ROUND_INTERVAL = 60.0


def bounded_float(value: Any, minimum: float, maximum: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return number


def bounded_int(value: Any, minimum: int, maximum: int, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if str(number) != str(value) and not isinstance(value, int):
        try:
            if float(value) != number:
                raise ValueError(f"{name} must be an integer")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be an integer") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a rate-limited UDP stream to the fixed Y13 lab victim."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help=f"seconds per round (maximum {MAX_DURATION:g})",
    )
    parser.add_argument(
        "--pps",
        type=int,
        default=200,
        help=f"packets per second (maximum {MAX_PACKETS_PER_SECOND})",
    )
    parser.add_argument(
        "--packet-size",
        type=int,
        default=1200,
        help=f"UDP payload bytes (maximum {MAX_PACKET_SIZE})",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="seconds between rounds",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        args.duration = bounded_float(args.duration, 0.1, MAX_DURATION, "duration")
        args.pps = bounded_int(args.pps, 1, MAX_PACKETS_PER_SECOND, "pps")
        args.packet_size = bounded_int(
            args.packet_size, 32, MAX_PACKET_SIZE, "packet size"
        )
        args.rounds = bounded_int(args.rounds, 1, MAX_ROUNDS, "rounds")
        args.interval = bounded_float(
            args.interval, 0, MAX_ROUND_INTERVAL, "interval"
        )
    except ValueError as error:
        parser.error(str(error))
    return args


def configuration_from_task() -> dict[str, Any]:
    task = json.load(sys.stdin)
    if not isinstance(task, dict) or task.get("task_type") != "udp_load":
        raise ValueError("expected a BotnetLab udp_load task")
    parameters = task.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("task parameters must be an object")
    return {
        "target": f"{VICTIM_IP}:{VICTIM_PORT}",
        "duration_seconds": bounded_float(
            parameters.get("duration_seconds", 10),
            0.1,
            MAX_DURATION,
            "duration_seconds",
        ),
        "packets_per_second": bounded_int(
            parameters.get("packets_per_second", 200),
            1,
            MAX_PACKETS_PER_SECOND,
            "packets_per_second",
        ),
        "udp_payload_bytes": bounded_int(
            parameters.get("udp_payload_bytes", 1200),
            32,
            MAX_PACKET_SIZE,
            "udp_payload_bytes",
        ),
        "rounds": bounded_int(parameters.get("rounds", 1), 1, MAX_ROUNDS, "rounds"),
        "round_interval_seconds": bounded_float(
            parameters.get("round_interval_seconds", 2),
            0,
            MAX_ROUND_INTERVAL,
            "round_interval_seconds",
        ),
        "dry_run": False,
        "command_id": str(task.get("command_id", "")),
    }


def configuration_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "target": f"{VICTIM_IP}:{VICTIM_PORT}",
        "duration_seconds": args.duration,
        "packets_per_second": args.pps,
        "udp_payload_bytes": args.packet_size,
        "rounds": args.rounds,
        "round_interval_seconds": args.interval,
        "dry_run": args.dry_run,
        "command_id": "manual",
    }


def make_payload(size: int) -> bytes:
    identity = f"Y13:{socket.gethostname()}:{os.getpid()}:".encode("ascii", "replace")
    return (identity + b"X" * size)[:size]


def run_round(sock: socket.socket, payload: bytes, duration: float, pps: int) -> int:
    deadline = time.monotonic() + duration
    next_send = time.monotonic()
    period = 1.0 / pps
    sent = 0

    while time.monotonic() < deadline:
        sock.sendto(payload, (VICTIM_IP, VICTIM_PORT))
        sent += 1
        next_send += period
        delay = next_send - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        elif delay < -1.0:
            next_send = time.monotonic()
    return sent


def main() -> int:
    handler_mode = len(sys.argv) == 1 and not sys.stdin.isatty()
    try:
        configuration = (
            configuration_from_task()
            if handler_mode
            else configuration_from_args(parse_args())
        )
    except (ValueError, json.JSONDecodeError) as error:
        print(f"invalid BotnetLab task: {error}", file=sys.stderr, flush=True)
        return 2
    if configuration["dry_run"]:
        print(json.dumps(configuration), flush=True)
        return 0

    duration = configuration["duration_seconds"]
    pps = configuration["packets_per_second"]
    packet_size = configuration["udp_payload_bytes"]
    rounds = configuration["rounds"]
    interval = configuration["round_interval_seconds"]
    payload = make_payload(packet_size)
    total_sent = 0
    started = time.monotonic()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for round_number in range(1, rounds + 1):
            print(
                f"round {round_number}/{rounds}: sending to "
                f"{VICTIM_IP}:{VICTIM_PORT} at {pps} pps for {duration:g}s",
                flush=True,
            )
            sent = run_round(sock, payload, duration, pps)
            total_sent += sent
            print(f"round {round_number}/{rounds}: sent {sent} packets", flush=True)
            if round_number < rounds and interval:
                time.sleep(interval)

    summary = {
        **configuration,
        "packets_sent": total_sent,
        "payload_bytes_sent": total_sent * len(payload),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    print(json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
