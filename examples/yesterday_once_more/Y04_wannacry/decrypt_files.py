#!/usr/bin/env python3
"""Victim-side recovery helper for the bounded WannaCry lab."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decrypt files in the WannaCry lab import_folder.")
    parser.add_argument("--target", default="/home/seed/import_folder")
    parser.add_argument("--key-file", default="/tmp/wannacry_lab_decryption_key.txt")
    parser.add_argument("--simulator", default="/opt/wannacry-lab/safe_ransomware_sim.py")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    key_file = Path(args.key_file)
    if not key_file.exists():
        print(f"decryption key not found: {key_file}", file=sys.stderr)
        print("Hint: search /tmp for the lab key file.", file=sys.stderr)
        return 1

    command = [
        sys.executable,
        args.simulator,
        "recover",
        "--target",
        args.target,
        "--key-file",
        str(key_file),
        "--i-understand-this-is-a-lab",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
