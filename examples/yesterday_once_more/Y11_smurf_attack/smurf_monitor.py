#!/usr/bin/env python3
"""Count ICMP echo replies that arrive at the Smurf victim."""

from __future__ import annotations

import argparse
import json
import socket
import struct
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor ICMP echo replies at the Smurf victim.")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--source-prefix", default="10.0.2.", help="count replies from this source prefix (amp IPs start with 10.0.2.)")
    parser.add_argument("--output", default="/tmp/smurf-monitor.json")
    return parser.parse_args()


def parse_icmp(packet: bytes) -> tuple[str, int] | None:
    if len(packet) < 28:
        return None

    ihl = (packet[0] & 0x0F) * 4
    if len(packet) < ihl + 8 or packet[9] != socket.IPPROTO_ICMP:
        return None

    source = socket.inet_ntoa(packet[12:16])
    icmp_type = packet[ihl]
    return source, icmp_type


def main() -> int:
    args = parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.settimeout(0.5)

    deadline = time.monotonic() + args.duration
    replies: list[str] = []
    total_icmp = 0

    print(f"Monitoring ICMP replies for {args.duration} seconds...")
    print(f"Counting replies from: {args.source_prefix}*")
    print()

    while time.monotonic() < deadline:
        try:
            packet, _ = sock.recvfrom(65535)
        except socket.timeout:
            continue

        parsed = parse_icmp(packet)
        if parsed is None:
            continue

        source, icmp_type = parsed
        total_icmp += 1
        if icmp_type == 0 and source.startswith(args.source_prefix):
            replies.append(source)
            print(f"  Received ICMP Reply from {source}")

    unique_sources = sorted(set(replies))
    summary = {
        "duration": args.duration,
        "source_prefix": args.source_prefix,
        "reply_count": len(replies),
        "unique_reply_sources": unique_sources,
        "total_icmp_seen": total_icmp,
        "amplification_factor": len(replies) / 3 if len(replies) > 0 else 0,  # assuming 3 attack packets
    }

    print()
    print("=" * 50)
    print("SMURF ATTACK RESULTS")
    print("=" * 50)
    print(f"Duration: {summary['duration']} seconds")
    print(f"Total ICMP packets seen: {summary['total_icmp_seen']}")
    print(f"ICMP Echo Replies from amplifiers: {summary['reply_count']}")
    print(f"Unique amplifier hosts responding: {len(summary['unique_reply_sources'])}")
    print(f"Amplification factor: {summary['amplification_factor']:.1f}x")
    print()
    print("Responding amplifier hosts:")
    for src in summary['unique_reply_sources']:
        count = replies.count(src)
        print(f"  {src}: {count} replies")

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
