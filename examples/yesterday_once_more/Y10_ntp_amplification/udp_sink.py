#!/usr/bin/env python3
"""Small UDP receiver used by the NTP amplification lab victim."""

from __future__ import annotations

import argparse
import socket
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record UDP packets sent to a lab victim.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--log", default="/var/log/ntp-like-victim.log")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"udp sink listening on {args.host}:{args.port}, log={args.log}", flush=True)

    with open(args.log, "a", encoding="utf-8") as handle:
        while True:
            data, source = sock.recvfrom(65535)
            line = "{:.3f} source={}:{} bytes={}\n".format(
                time.time(),
                source[0],
                source[1],
                len(data),
            )
            handle.write(line)
            handle.flush()
            print(line, end="", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
