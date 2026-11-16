#!/usr/bin/env python3
"""
Lab-only TCP sequence oracle for Mitnick-attack demonstrations.

This helper runs on the target LAN inside an isolated emulator. It passively
sniffs TCP packet headers and exposes selected metadata through a UDP query
interface. It does not capture packet payloads.
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import threading
import time
from collections import deque
from typing import Deque, Dict, Iterable, Optional, Tuple


ETH_P_IP = 0x0800
IPPROTO_TCP = 6


def ipv4(raw: bytes) -> str:
    return socket.inet_ntoa(raw)


def allowed(ip_address: str, prefixes: Iterable[str]) -> bool:
    return any(ip_address.startswith(prefix) for prefix in prefixes)


def parse_tcp_packet(frame: bytes) -> Optional[Dict[str, object]]:
    if len(frame) < 54:
        return None

    eth_type = struct.unpack("!H", frame[12:14])[0]
    if eth_type != ETH_P_IP:
        return None

    ip_start = 14
    version_ihl = frame[ip_start]
    version = version_ihl >> 4
    ihl = (version_ihl & 0x0F) * 4
    if version != 4 or len(frame) < ip_start + ihl + 20:
        return None

    protocol = frame[ip_start + 9]
    if protocol != IPPROTO_TCP:
        return None

    total_length = struct.unpack("!H", frame[ip_start + 2 : ip_start + 4])[0]
    source_ip = ipv4(frame[ip_start + 12 : ip_start + 16])
    destination_ip = ipv4(frame[ip_start + 16 : ip_start + 20])

    tcp_start = ip_start + ihl
    source_port, destination_port, sequence, acknowledgement, offset_flags, window = struct.unpack(
        "!HHIIHH",
        frame[tcp_start : tcp_start + 16],
    )
    tcp_header_length = ((offset_flags >> 12) & 0x0F) * 4
    flags = offset_flags & 0x01FF
    payload_length = max(total_length - ihl - tcp_header_length, 0)

    return {
        "time": time.time(),
        "src": source_ip,
        "dst": destination_ip,
        "sport": source_port,
        "dport": destination_port,
        "seq": sequence,
        "ack": acknowledgement,
        "flags": flags,
        "flags_text": flags_to_text(flags),
        "window": window,
        "payload_len": payload_length,
    }


def flags_to_text(flags: int) -> str:
    names = [
        (0x100, "NS"),
        (0x080, "CWR"),
        (0x040, "ECE"),
        (0x020, "URG"),
        (0x010, "ACK"),
        (0x008, "PSH"),
        (0x004, "RST"),
        (0x002, "SYN"),
        (0x001, "FIN"),
    ]
    text = [name for bit, name in names if flags & bit]
    return ",".join(text) if text else "NONE"


class PacketStore:
    def __init__(self, max_packets: int):
        self._packets: Deque[Dict[str, object]] = deque(maxlen=max_packets)
        self._lock = threading.Lock()

    def add(self, packet: Dict[str, object]) -> None:
        with self._lock:
            self._packets.append(packet)

    def query(
        self,
        src: Optional[str] = None,
        dst: Optional[str] = None,
        sport: Optional[int] = None,
        dport: Optional[int] = None,
        limit: int = 5,
    ) -> list[Dict[str, object]]:
        with self._lock:
            packets = list(self._packets)

        matches = []
        for packet in reversed(packets):
            if src and packet["src"] != src:
                continue
            if dst and packet["dst"] != dst:
                continue
            if sport is not None and packet["sport"] != sport:
                continue
            if dport is not None and packet["dport"] != dport:
                continue
            matches.append(packet)
            if len(matches) >= limit:
                break
        return matches

    def summary(self) -> Dict[str, object]:
        with self._lock:
            packets = list(self._packets)
        return {
            "stored_packets": len(packets),
            "oldest_time": packets[0]["time"] if packets else None,
            "newest_time": packets[-1]["time"] if packets else None,
        }


def sniff_loop(store: PacketStore, iface: str, local_prefixes: list[str]) -> None:
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_IP))
    if iface:
        sock.bind((iface, 0))

    while True:
        frame, _ = sock.recvfrom(65535)
        packet = parse_tcp_packet(frame)
        if packet is None:
            continue
        if local_prefixes and not (
            allowed(str(packet["src"]), local_prefixes) or allowed(str(packet["dst"]), local_prefixes)
        ):
            continue
        store.add(packet)


def parse_query(data: bytes) -> Tuple[str, Dict[str, object]]:
    text = data.decode(errors="ignore").strip()
    if not text:
        return "summary", {}

    if text.startswith("{"):
        obj = json.loads(text)
        command = str(obj.pop("command", "query"))
        return command, obj

    parts = text.split()
    command = parts[0].lower()
    params: Dict[str, object] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key in {"sport", "dport", "limit"}:
            params[key] = int(value)
        else:
            params[key] = value
    return command, params


def udp_loop(store: PacketStore, args: argparse.Namespace) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"TCP sequence oracle listening on udp://{args.host}:{args.port}", flush=True)

    while True:
        data, client = sock.recvfrom(4096)
        client_ip = client[0]
        if args.allowed_client_prefix and not allowed(client_ip, args.allowed_client_prefix):
            continue

        try:
            command, params = parse_query(data)
            if command == "summary":
                response = store.summary()
            elif command == "query":
                response = {
                    "packets": store.query(
                        src=params.get("src"),
                        dst=params.get("dst"),
                        sport=params.get("sport"),
                        dport=params.get("dport"),
                        limit=int(params.get("limit", args.default_limit)),
                    )
                }
            else:
                response = {"error": f"unknown command: {command}"}
        except Exception as exc:
            response = {"error": str(exc)}

        sock.sendto((json.dumps(response, indent=2, sort_keys=True) + "\n").encode(), client)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lab-only TCP sequence oracle.")
    parser.add_argument("--iface", default="", help="interface to sniff; empty means all")
    parser.add_argument("--host", default="0.0.0.0", help="UDP server bind address")
    parser.add_argument("--port", type=int, default=9090, help="UDP query port")
    parser.add_argument("--max-packets", type=int, default=500)
    parser.add_argument("--default-limit", type=int, default=5)
    parser.add_argument(
        "--local-prefix",
        action="append",
        default=["10."],
        help="record packets with src or dst matching this prefix; repeatable",
    )
    parser.add_argument(
        "--allowed-client-prefix",
        action="append",
        default=["10."],
        help="answer UDP clients matching this prefix; repeatable",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = PacketStore(max_packets=args.max_packets)
    sniffer = threading.Thread(target=sniff_loop, args=(store, args.iface, args.local_prefix), daemon=True)
    sniffer.start()
    udp_loop(store, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
