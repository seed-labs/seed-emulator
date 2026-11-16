#!/usr/bin/env python3
"""Drain Y13 attack datagrams without producing reply traffic."""

from __future__ import annotations

import argparse
import socket
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Y13 victim UDP sink.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    sock.bind((args.host, args.port))
    sock.settimeout(1.0)
    print(f"Y13 UDP sink listening on {args.host}:{args.port}", flush=True)

    packets = 0
    byte_count = 0
    sample_started = time.monotonic()
    while True:
        try:
            payload, _source = sock.recvfrom(65535)
            packets += 1
            byte_count += len(payload)
        except socket.timeout:
            pass

        now = time.monotonic()
        if now - sample_started >= 1.0:
            print(f"received packets={packets} payload_bytes={byte_count}", flush=True)
            packets = 0
            byte_count = 0
            sample_started = now


if __name__ == "__main__":
    raise SystemExit(main())
