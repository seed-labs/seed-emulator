#!/usr/bin/env python3
"""Seed the first SQL Slammer lab infection."""

from __future__ import annotations

import argparse
import socket

from slammer_packet import build_packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send one SQL Slammer lab replica packet.")
    parser.add_argument("target", help="target IP address")
    parser.add_argument("--port", type=int, default=1434)
    parser.add_argument("--token", default="seedemu-slammer-lab")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = build_packet(parent="initial-seed", generation=0, token=args.token)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (args.target, args.port))
    print(f"sent_bytes={len(packet)} target={args.target}:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
