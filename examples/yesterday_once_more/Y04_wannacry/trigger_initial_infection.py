#!/usr/bin/env python3
"""Trigger the first lab infection for the WannaCry emulator example."""

from __future__ import annotations

import argparse
import socket


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger one WannaCry lab infection.")
    parser.add_argument("target", help="target IP address")
    parser.add_argument("--port", type=int, default=445)
    parser.add_argument("--token", default="seedemu-wannacry-lab")
    parser.add_argument("--timeout", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = f"INFECT {args.token}".encode()
    with socket.create_connection((args.target, args.port), timeout=args.timeout) as sock:
        sock.sendall(request)
        sock.settimeout(args.timeout)
        response = sock.recv(1024).decode(errors="ignore").strip()
    print(response)
    return 0 if response.startswith("OK") or response.startswith("ALREADY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
