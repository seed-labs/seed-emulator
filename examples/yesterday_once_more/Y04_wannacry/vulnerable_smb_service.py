#!/usr/bin/env python3
"""
Lab-only vulnerable SMB-like service for the WannaCry example.

This is not SMB and it does not implement any real exploit. It listens for a
small lab trigger message and then runs the bounded ransomware simulator against
the local import_folder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time


STATUS_FILE = "/tmp/wannacry_lab_vulnerable_service.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lab-only vulnerable SMB-like service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=445)
    parser.add_argument("--token", default="seedemu-wannacry-lab")
    parser.add_argument("--target", default="/home/seed/import_folder")
    parser.add_argument("--simulator", default="/opt/wannacry-lab/safe_ransomware_sim.py")
    parser.add_argument("--decrypt-helper", default="/opt/wannacry-lab/decrypt_files.py")
    parser.add_argument("--worm", default="/opt/wannacry-lab/wannacry_worm.py")
    parser.add_argument("--targets-file", default="/opt/wannacry-lab/targets.txt")
    parser.add_argument("--key-store", default="/tmp/wannacry_lab_keys")
    parser.add_argument("--propagate", dest="propagate", action="store_true", default=True)
    parser.add_argument("--no-propagate", dest="propagate", action="store_false")
    return parser.parse_args()


def write_status(status: dict[str, object]) -> None:
    status_path = Path(STATUS_FILE)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_simulator(args: argparse.Namespace) -> tuple[int, str, str]:
    command = [
        sys.executable,
        args.simulator,
        "encrypt",
        "--target",
        args.target,
        "--key-store",
        args.key_store,
        "--i-understand-this-is-a-lab",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def launch_worm(args: argparse.Namespace) -> int | None:
    if not args.propagate:
        return None

    marker = Path("/tmp/wannacry_lab_worm_started")
    if marker.exists():
        return None

    command = [
        sys.executable,
        args.worm,
        "--targets-file",
        args.targets_file,
        "--port",
        str(args.port),
        "--token",
        args.token,
        "--once",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return process.pid


def install_recovery_helper(args: argparse.Namespace) -> str:
    target_dir = Path(args.target)
    helper_target = target_dir / "DECRYPT_FILES.py"
    helper_source = Path(args.decrypt_helper)
    if helper_source.exists():
        helper_target.write_text(helper_source.read_text(encoding="utf-8"), encoding="utf-8")
        helper_target.chmod(0o755)
        return str(helper_target)
    return ""


def handle_client(conn: socket.socket, peer: tuple[str, int], args: argparse.Namespace) -> None:
    request = conn.recv(1024).decode(errors="ignore").strip()
    if request == "STATUS":
        status = Path(STATUS_FILE).read_text(encoding="utf-8") if Path(STATUS_FILE).exists() else "{}"
        conn.sendall(status.encode())
        return

    expected = f"INFECT {args.token}"
    if request != expected:
        conn.sendall(b"ERROR unsupported lab request\n")
        return

    status = {
        "status": "infection_requested",
        "peer": f"{peer[0]}:{peer[1]}",
        "time": time.time(),
        "target": args.target,
    }
    write_status(status)

    code, stdout, stderr = run_simulator(args)
    recovery_helper = install_recovery_helper(args) if code == 0 else ""
    worm_pid = launch_worm(args) if code == 0 else None
    status.update(
        {
            "status": "encrypted" if code == 0 else "failed",
            "exit": code,
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
            "recovery_helper": recovery_helper,
            "worm_pid": worm_pid,
            "finished_at": time.time(),
        }
    )
    write_status(status)

    if code == 0:
        conn.sendall(b"OK encrypted lab import_folder; propagation started\n")
    elif "already marked encrypted" in stderr:
        conn.sendall(b"ALREADY encrypted lab import_folder\n")
    else:
        conn.sendall(f"ERROR simulator failed: {code}\n".encode())


def main() -> int:
    args = parse_args()
    Path(args.target).mkdir(parents=True, exist_ok=True)
    write_status({"status": "listening", "target": args.target, "port": args.port})

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.host, args.port))
    sock.listen(16)
    print(f"lab vulnerable service listening on {args.host}:{args.port}", flush=True)

    while True:
        conn, peer = sock.accept()
        with conn:
            handle_client(conn, peer, args)


if __name__ == "__main__":
    raise SystemExit(main())
