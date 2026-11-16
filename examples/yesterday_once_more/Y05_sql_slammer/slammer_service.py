#!/usr/bin/env python3
"""Lab-only vulnerable SQL Resolution-like UDP service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

from slammer_packet import local_ip, parse_packet


STATUS_FILE = "/tmp/slammer_lab_status.json"
REPLICA_FILE = "/tmp/slammer_lab_last_replica_packet.json"
START_MARKER = "/tmp/slammer_lab_worm_started"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lab-only SQL Slammer vulnerable UDP service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=1434)
    parser.add_argument("--token", default="seedemu-slammer-lab")
    parser.add_argument("--worm", default="/opt/slammer-lab/slammer_worm.py")
    parser.add_argument("--targets-file", default="/opt/slammer-lab/targets.txt")
    parser.add_argument("--packet-rate", type=float, default=80.0)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--patched", action="store_true", help="listen but do not become infected")
    return parser.parse_args()


def write_status(status: dict[str, object]) -> None:
    path = Path(STATUS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_status() -> dict[str, object]:
    path = Path(STATUS_FILE)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def launch_worm(args: argparse.Namespace, generation: int) -> int | None:
    marker = Path(START_MARKER)
    if marker.exists():
        return None
    marker.write_text(str(time.time()) + "\n", encoding="utf-8")
    command = [
        sys.executable,
        args.worm,
        "--targets-file",
        args.targets_file,
        "--port",
        str(args.port),
        "--token",
        args.token,
        "--packet-rate",
        str(args.packet_rate),
        "--duration",
        str(args.duration),
        "--generation",
        str(generation),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return process.pid


def handle_packet(data: bytes, peer: tuple[str, int], args: argparse.Namespace) -> None:
    if data.strip() == b"STATUS":
        return

    try:
        packet = parse_packet(data, token=args.token)
    except Exception as exc:
        status = load_status()
        status.update({"last_error": str(exc), "last_bad_packet_from": f"{peer[0]}:{peer[1]}"})
        write_status(status)
        return

    if args.patched:
        write_status(
            {
                "status": "patched",
                "address": local_ip(),
                "last_packet_from": f"{peer[0]}:{peer[1]}",
                "last_generation_seen": packet.get("generation"),
                "infected": False,
            }
        )
        return

    current = load_status()
    if current.get("infected"):
        current["duplicate_packets"] = int(current.get("duplicate_packets", 0)) + 1
        current["last_packet_from"] = f"{peer[0]}:{peer[1]}"
        write_status(current)
        return

    generation = int(packet.get("generation", 0)) + 1
    Path(REPLICA_FILE).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    worm_pid = launch_worm(args, generation)
    write_status(
        {
            "status": "infected",
            "infected": True,
            "address": local_ip(),
            "infected_at": time.time(),
            "infected_by": f"{peer[0]}:{peer[1]}",
            "generation": generation,
            "replica_packet_saved": REPLICA_FILE,
            "worm_pid": worm_pid,
            "duplicate_packets": 0,
        }
    )


def main() -> int:
    args = parse_args()
    write_status({"status": "patched" if args.patched else "listening", "infected": False, "address": local_ip()})
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"SQL Slammer lab UDP service listening on {args.host}:{args.port}", flush=True)

    while True:
        data, peer = sock.recvfrom(8192)
        handle_packet(data, peer, args)


if __name__ == "__main__":
    raise SystemExit(main())
