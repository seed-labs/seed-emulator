#!/usr/bin/env python3
"""Bounded UDP echo/chargen-like amplifier for the Y11 Fraggle lab."""

from __future__ import annotations

import argparse
import socket
import time


def allowed(address: str, prefixes: list[str]) -> bool:
    return any(address.startswith(prefix) for prefix in prefixes)


def build_response(mode: str, request: bytes, response_size: int) -> bytes:
    if mode == "echo":
        if request:
            return request[:response_size]
        return b"SEED-FRAGGLE-LAB\n"

    alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    prefix = b"SEED-FRAGGLE-LAB-CHARGEN "
    body = prefix + alphabet + b"\n"
    repeats = (response_size // len(body)) + 1
    return (body * repeats)[:response_size]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lab-only UDP amplifier daemon.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=19, help="UDP port to listen on")
    parser.add_argument("--mode", choices=["echo", "chargen"], default="chargen")
    parser.add_argument("--response-size", type=int, default=512)
    parser.add_argument("--max-response-size", type=int, default=1200)
    parser.add_argument("--allowed-prefix", action="append", default=["10."])
    parser.add_argument("--log", default="/var/log/fraggle-amplifier.log")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    response_size = max(1, min(args.response_size, args.max_response_size))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind((args.host, args.port))

    with open(args.log, "a", encoding="utf-8") as log:
        print(
            "fraggle amplifier listening udp://{}:{} mode={} response_size={}".format(
                args.host,
                args.port,
                args.mode,
                response_size,
            ),
            file=log,
            flush=True,
        )

        while True:
            data, client = sock.recvfrom(65535)
            client_ip, client_port = client
            if not allowed(client_ip, args.allowed_prefix):
                print(
                    "{} ignored request from {}:{} bytes={}".format(
                        time.time(),
                        client_ip,
                        client_port,
                        len(data),
                    ),
                    file=log,
                    flush=True,
                )
                continue

            response = build_response(args.mode, data, response_size)
            sock.sendto(response, client)
            print(
                "{} replied to {}:{} request_bytes={} response_bytes={}".format(
                    time.time(),
                    client_ip,
                    client_port,
                    len(data),
                    len(response),
                ),
                file=log,
                flush=True,
            )


if __name__ == "__main__":
    raise SystemExit(main())
