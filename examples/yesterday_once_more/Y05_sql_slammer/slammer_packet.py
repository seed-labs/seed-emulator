#!/usr/bin/env python3
"""Shared packet helpers for the SQL Slammer lab simulator."""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import time
from typing import Dict


PACKET_TYPE = "SQL_SLAMMER_LAB_REPLICA"
TOKEN = "seedemu-slammer-lab"
BODY = (
    "This is a benign SEED Emulator SQL Slammer lab replica. "
    "The real Slammer worm carried native x86 code inside one UDP packet. "
    "This lab packet carries only this descriptor and a token."
)


def build_packet(parent: str = "seed", generation: int = 0, token: str = TOKEN) -> bytes:
    body = BODY.encode("utf-8")
    packet: Dict[str, object] = {
        "type": PACKET_TYPE,
        "token": token,
        "parent": parent,
        "generation": generation,
        "created_at": time.time(),
        "body_encoding": "base64",
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body": base64.b64encode(body).decode("ascii"),
    }
    return json.dumps(packet, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_packet(data: bytes, token: str = TOKEN) -> Dict[str, object]:
    packet = json.loads(data.decode("utf-8"))
    if packet.get("type") != PACKET_TYPE:
        raise ValueError("not a SQL Slammer lab replica packet")
    if packet.get("token") != token:
        raise ValueError("invalid lab token")
    body = base64.b64decode(str(packet.get("body", "")))
    if hashlib.sha256(body).hexdigest() != packet.get("body_sha256"):
        raise ValueError("replica body checksum mismatch")
    return packet


def local_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.0.0.1", 1))
        return probe.getsockname()[0]
    except OSError:
        return socket.gethostname()
    finally:
        probe.close()
