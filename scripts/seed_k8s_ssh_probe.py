#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def parse_node_spec(value: str) -> tuple[str, str]:
    for separator in ("=", ":"):
        if separator in value:
            name, ip = value.split(separator, 1)
            name = name.strip()
            ip = ip.strip()
            if name and ip:
                return name, ip
    raise argparse.ArgumentTypeError(f"invalid --node value: {value!r}; expected name=ip")


def build_ssh_command(user: str, key_path: str, timeout_seconds: int, ip: str, remote_command: str) -> list[str]:
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        f"ConnectTimeout={timeout_seconds}",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-n",
        "-i",
        key_path,
        f"{user}@{ip}",
        remote_command,
    ]


def _clean_output(value: str) -> str:
    return " ".join(value.strip().split())


def run_remote_command(command: Sequence[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        text=True,
        capture_output=True,
        check=False,
        timeout=max(timeout_seconds + 5, 10),
    )


def probe_node(name: str, ip: str, user: str, key_path: str, timeout_seconds: int) -> dict[str, object]:
    hostname_result = run_remote_command(
        build_ssh_command(user, key_path, timeout_seconds, ip, "hostname"),
        timeout_seconds,
    )
    reachable = hostname_result.returncode == 0
    hostname = _clean_output(hostname_result.stdout) if reachable else ""
    error_text = _clean_output(hostname_result.stderr or hostname_result.stdout)

    sudo_ok = False
    sudo_error = ""
    if reachable:
        sudo_result = run_remote_command(
            build_ssh_command(user, key_path, timeout_seconds, ip, "sudo -n true"),
            timeout_seconds,
        )
        sudo_ok = sudo_result.returncode == 0
        sudo_error = _clean_output(sudo_result.stderr or sudo_result.stdout)

    return {
        "name": name,
        "management_ip": ip,
        "reachable": reachable,
        "hostname": hostname,
        "sudo_nopasswd_ok": sudo_ok,
        "ssh_error": "" if reachable else error_text,
        "sudo_error": "" if sudo_ok else sudo_error,
    }


def collect_probe_summary(user: str, key_path: str, timeout_seconds: int, nodes: Sequence[tuple[str, str]]) -> dict[str, object]:
    expanded_key_path = str(Path(key_path).expanduser())
    key_exists = Path(expanded_key_path).is_file()
    results: list[dict[str, object]] = []

    if key_exists:
        results = [probe_node(name, ip, user, expanded_key_path, timeout_seconds) for name, ip in nodes if ip]
    else:
        results = [
            {
                "name": name,
                "management_ip": ip,
                "reachable": False,
                "hostname": "",
                "sudo_nopasswd_ok": False,
                "ssh_error": f"key not found: {expanded_key_path}",
                "sudo_error": "",
            }
            for name, ip in nodes
            if ip
        ]

    ssh_access_ok = bool(results) and all(bool(item.get("reachable")) for item in results)
    sudo_ok = bool(results) and all(bool(item.get("sudo_nopasswd_ok")) for item in results)

    return {
        "user": user,
        "key_path": expanded_key_path,
        "key_exists": key_exists,
        "timeout_seconds": timeout_seconds,
        "nodes": results,
        "ssh_access_ok": ssh_access_ok,
        "sudo_nopasswd_ok": sudo_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe SSH access to K3s/KVM nodes")
    parser.add_argument("--user", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--json-output", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--node", action="append", default=[], help="repeatable node spec in name=ip form")
    args = parser.parse_args()

    nodes = [parse_node_spec(value) for value in args.node]
    summary = collect_probe_summary(args.user, args.key, args.timeout, nodes)
    rendered = json.dumps(summary, indent=2)

    if args.json_output:
        output_path = Path(args.json_output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

    if args.strict and (not summary["ssh_access_ok"] or not summary["sudo_nopasswd_ok"]):
        return 1
    if not summary["key_exists"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
