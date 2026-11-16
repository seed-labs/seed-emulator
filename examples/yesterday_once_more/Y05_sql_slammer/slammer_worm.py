#!/usr/bin/env python3
"""Bounded SQL Slammer-style UDP worm simulator."""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import socket
import time

from slammer_packet import build_packet, local_ip


LOG_FILE = "/tmp/slammer_lab_worm.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded SQL Slammer-style UDP worm simulator.")
    parser.add_argument("--targets-file", default="/opt/slammer-lab/targets.txt")
    parser.add_argument("--port", type=int, default=1434)
    parser.add_argument("--token", default="seedemu-slammer-lab")
    parser.add_argument("--packet-rate", type=float, default=80.0)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--generation", type=int, default=0)
    parser.add_argument("--allow-prefix", action="append", default=["10."])
    return parser.parse_args()


def log(message: str) -> None:
    path = Path(LOG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{time.time():.3f} {message}\n")


def load_targets(path: str, allowed_prefixes: list[str]) -> list[str]:
    targets = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        target = line.strip()
        if not target or target.startswith("#"):
            continue
        if any(target.startswith(prefix) for prefix in allowed_prefixes):
            targets.append(target)
    random.shuffle(targets)
    return targets


def main() -> int:
    args = parse_args()
    targets = load_targets(args.targets_file, args.allow_prefix)
    if not targets:
        log("no targets")
        print("packets_sent=0")
        return 0

    delay = 1.0 / args.packet_rate if args.packet_rate > 0 else 0.0
    packet = build_packet(parent=local_ip(), generation=args.generation, token=args.token)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    deadline = time.monotonic() + args.duration
    sent = 0
    index = 0

    log(f"start targets={len(targets)} rate={args.packet_rate} duration={args.duration} generation={args.generation}")
    while time.monotonic() < deadline:
        target = targets[index % len(targets)]
        sock.sendto(packet, (target, args.port))
        sent += 1
        index += 1
        if delay > 0:
            time.sleep(delay)

    log(f"finish packets_sent={sent}")
    print(f"packets_sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
