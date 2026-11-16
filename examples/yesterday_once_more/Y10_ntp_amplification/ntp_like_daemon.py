#!/usr/bin/env python3
"""
Lab-only NTP-like UDP daemon for amplification demonstrations.

This is not a real NTP implementation. It mimics one historical NTP failure
mode: a small monitor-style request can produce a much larger UDP response.

The optional reflection command is a Docker/emulator-friendly substitute for
source-IP spoofing. Enable it only in isolated labs with --reflect-token.
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple


Client = Tuple[str, int]


def build_payload(size: int, request: bytes, client: Client) -> bytes:
    """Build a deterministic response of exactly size bytes."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()).encode()
    prefix = (
        b"NTP-LIKE-MONITOR-RESPONSE\n"
        + b"server=seedemu-lab-ntp-like\n"
        + b"time="
        + now
        + b"\n"
        + b"client="
        + f"{client[0]}:{client[1]}".encode()
        + b"\n"
        + b"request-len="
        + str(len(request)).encode()
        + b"\n"
        + b"entries=\n"
    )

    line = b"  peer=192.0.2.1 stratum=2 delay=0.031 offset=0.002 jitter=0.004\n"
    if size <= len(prefix):
        return prefix[:size]

    repeats = ((size - len(prefix)) // len(line)) + 1
    payload = prefix + (line * repeats)
    return payload[:size]


def allow_by_prefix(ip_address: str, prefixes: list[str]) -> bool:
    """Small string-prefix allowlist for simple lab subnets such as 10."""
    if not prefixes:
        return True
    return any(ip_address.startswith(prefix) for prefix in prefixes)


def rate_limited(client: Client, history: Dict[str, Deque[float]], per_second: int) -> bool:
    if per_second <= 0:
        return False

    now = time.monotonic()
    source_ip = client[0]
    q = history[source_ip]
    while q and now - q[0] > 1.0:
        q.popleft()

    if len(q) >= per_second:
        return True

    q.append(now)
    return False


def parse_reflection_request(
    request: bytes,
    token: Optional[str],
    allowed_target_prefixes: list[str],
) -> Optional[Tuple[str, int]]:
    if token is None:
        return None

    parts = request.decode(errors="ignore").strip().split()
    if len(parts) != 4 or parts[0].lower() != "reflect" or parts[1] != token:
        return None

    target_ip = parts[2]
    try:
        target_port = int(parts[3])
    except ValueError:
        return None

    if target_port < 1 or target_port > 65535:
        return None
    if not allow_by_prefix(target_ip, allowed_target_prefixes):
        return None

    return (target_ip, target_port)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a lab-only NTP-like UDP daemon for amplification demonstrations."
    )
    parser.add_argument("--host", default="0.0.0.0", help="local address to bind")
    parser.add_argument("--port", type=int, default=123, help="UDP port to listen on")
    parser.add_argument(
        "--response-size",
        type=int,
        default=1200,
        help="bytes sent in each synthetic monitor response",
    )
    parser.add_argument(
        "--trigger",
        default="monlist",
        help="request text that triggers direct large replies",
    )
    parser.add_argument(
        "--allowed-prefix",
        action="append",
        default=[],
        help="client IP prefix allowed to query, e.g. 10. or 192.168.; repeatable",
    )
    parser.add_argument(
        "--reflect-token",
        help="enable lab reflection requests: 'reflect TOKEN TARGET_IP TARGET_PORT'",
    )
    parser.add_argument(
        "--reflect-target-prefix",
        action="append",
        default=[],
        help="target IP prefix allowed for reflection; repeatable",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=0,
        help="max replies per source IP per second; 0 disables rate limiting",
    )
    parser.add_argument("--quiet", action="store_true", help="do not print one log line per request")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.response_size < 1:
        print("--response-size must be positive", file=sys.stderr)
        return 2
    if args.response_size > 65507:
        print("--response-size must be <= 65507 for UDP/IPv4", file=sys.stderr)
        return 2

    history: Dict[str, Deque[float]] = defaultdict(deque)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))

    print(
        "lab NTP-like daemon listening on udp://{}:{} response_size={} trigger={!r}".format(
            args.host, args.port, args.response_size, args.trigger
        ),
        flush=True,
    )

    while True:
        request, client = sock.recvfrom(4096)
        client_ip = client[0]

        if not allow_by_prefix(client_ip, args.allowed_prefix):
            if not args.quiet:
                print(f"drop client={client_ip} reason=not-allowed", flush=True)
            continue

        if rate_limited(client, history, args.rate_limit):
            response = b"NTP-LIKE-ERROR rate limited\n"
            destination = client
        else:
            reflection_target = parse_reflection_request(
                request,
                args.reflect_token,
                args.reflect_target_prefix,
            )
            if reflection_target is not None:
                response = build_payload(args.response_size, request, client)
                destination = reflection_target
            elif request.strip().lower() == args.trigger.encode().lower():
                response = build_payload(args.response_size, request, client)
                destination = client
            else:
                response = b"NTP-LIKE-ERROR unsupported request\n"
                destination = client

        sock.sendto(response, destination)

        if not args.quiet:
            amp = len(response) / max(len(request), 1)
            print(
                "reply source={} destination={}:{} request_bytes={} response_bytes={} amplification={:.1f}x".format(
                    f"{client[0]}:{client[1]}",
                    destination[0],
                    destination[1],
                    len(request),
                    len(response),
                    amp,
                ),
                flush=True,
            )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
        raise SystemExit(130)
