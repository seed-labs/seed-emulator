#!/usr/bin/env python3
"""
Safe WannaCry-style ransomware simulator for SEED Emulator labs.

This script is intentionally constrained. It only operates on a directory named
"import_folder", skips hidden state files, limits file sizes, and provides a
recovery command. It is for teaching the ransomware workflow with fake files,
not for real-world use.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time
from typing import Dict, Iterable, List


STATE_FILE = ".wannacry_lab_state.json"
RANSOM_NOTE = "README_RECOVER_FILES.txt"
ENCRYPTED_SUFFIX = ".wncry_lab"
DEFAULT_KEY_STORE = "/tmp/wannacry_lab_keys"
DEFAULT_VISIBLE_KEY = "/tmp/wannacry_lab_decryption_key.txt"
MAX_FILE_SIZE = 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024


SAMPLE_FILES: Dict[str, str] = {
    "class_notes.txt": "These are fake class notes for the ransomware lab.\n",
    "project_plan.txt": "Milestone 1: build. Milestone 2: test. Milestone 3: recover.\n",
    "budget.csv": "item,cost\nservers,1200\ntraining,300\nbackup,500\n",
    "photos/family_trip.txt": "This placeholder represents an important personal file.\n",
    "research/data.txt": "fake_id,value\n1,42\n2,99\n3,123\n",
}


def require_lab_ack(args: argparse.Namespace) -> None:
    if not args.i_understand_this_is_a_lab:
        raise SystemExit(
            "Refusing to run. Add --i-understand-this-is-a-lab to confirm this is an isolated lab."
        )


def resolve_target(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    if target.name != "import_folder":
        raise SystemExit('Refusing to operate: target directory must be named "import_folder".')
    return target


def iter_plain_files(target: Path) -> Iterable[Path]:
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {STATE_FILE, RANSOM_NOTE}:
            continue
        if path.name.startswith("."):
            continue
        if path.suffix == ENCRYPTED_SUFFIX:
            continue
        yield path


def iter_encrypted_files(target: Path) -> Iterable[Path]:
    for path in sorted(target.rglob(f"*{ENCRYPTED_SUFFIX}")):
        if path.is_file():
            yield path


def keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: List[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
        counter += 1
    return b"".join(blocks)[:length]


def transform(data: bytes, key: bytes, nonce: bytes) -> bytes:
    stream = keystream(key, nonce, len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def load_state(target: Path) -> Dict[str, object]:
    path = target / STATE_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(target: Path, state: Dict[str, object]) -> None:
    (target / STATE_FILE).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_sample_files(args: argparse.Namespace) -> int:
    target = resolve_target(args.target)
    target.mkdir(parents=True, exist_ok=True)
    for relative, content in SAMPLE_FILES.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not args.force:
            continue
        path.write_text(content, encoding="utf-8")
    print(f"created sample files under {target}")
    return 0


def choose_victim_id(args: argparse.Namespace, target: Path) -> str:
    if args.victim_id:
        return args.victim_id
    raw = f"{socket.gethostname()}:{target}:{time.time()}:{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def write_ransom_note(target: Path, victim_id: str, encrypted_count: int) -> None:
    note = f"""\
YOUR LAB FILES HAVE BEEN ENCRYPTED

This is a SEED Emulator ransomware simulation, not real malware.

Victim ID: {victim_id}
Encrypted files: {encrypted_count}

Educational scenario:
  1. The victim's fake files in import_folder were encrypted.
  2. A later lab step will model blockchain payment.
  3. After payment, the recovery key will be released.
  4. The victim can run the recovery command to restore the files.

Do not use this script outside the isolated emulator.
"""
    (target / RANSOM_NOTE).write_text(note, encoding="utf-8")


def encrypt(args: argparse.Namespace) -> int:
    require_lab_ack(args)
    target = resolve_target(args.target)
    if not target.exists():
        raise SystemExit(f"target does not exist: {target}")

    state = load_state(target)
    if state.get("status") == "encrypted":
        raise SystemExit("target is already marked encrypted")

    key = secrets.token_bytes(32)
    victim_id = choose_victim_id(args, target)
    encrypted_files = []
    total_bytes = 0

    for path in iter_plain_files(target):
        size = path.stat().st_size
        if size > args.max_file_size:
            print(f"skip large file: {path}", file=sys.stderr)
            continue
        if total_bytes + size > args.max_total_bytes:
            print("total byte limit reached; stopping", file=sys.stderr)
            break

        data = path.read_bytes()
        nonce = secrets.token_bytes(16)
        ciphertext = transform(data, key, nonce)
        encrypted_path = path.with_name(path.name + ENCRYPTED_SUFFIX)
        encrypted_path.write_bytes(base64.b64encode(nonce + ciphertext))
        path.unlink()
        encrypted_files.append(str(path.relative_to(target)))
        total_bytes += size

    key_store = Path(args.key_store).expanduser().resolve()
    key_store.mkdir(parents=True, exist_ok=True)
    key_file = key_store / f"{victim_id}.key"
    key_file.write_text(key.hex() + "\n", encoding="utf-8")
    os.chmod(key_file, 0o600)
    visible_key_file = Path(args.visible_key_file).expanduser().resolve()
    visible_key_file.parent.mkdir(parents=True, exist_ok=True)
    visible_key_file.write_text(key.hex() + "\n", encoding="utf-8")
    os.chmod(visible_key_file, 0o600)

    state = {
        "status": "encrypted",
        "victim_id": victim_id,
        "encrypted_at": time.time(),
        "encrypted_files": encrypted_files,
        "encrypted_count": len(encrypted_files),
        "total_plaintext_bytes": total_bytes,
        "key_store_hint": str(key_file),
        "visible_key_hint": str(visible_key_file),
        "algorithm": "lab-xor-sha256-stream",
    }
    save_state(target, state)
    write_ransom_note(target, victim_id, len(encrypted_files))

    print(f"victim_id={victim_id}")
    print(f"encrypted_files={len(encrypted_files)}")
    print(f"key_saved_for_lab_controller={key_file}")
    print(f"visible_lab_decryption_key={visible_key_file}")
    return 0


def read_key(args: argparse.Namespace) -> bytes:
    if args.key:
        return bytes.fromhex(args.key.strip())
    if args.key_file:
        return bytes.fromhex(Path(args.key_file).read_text(encoding="utf-8").strip())
    raise SystemExit("recovery requires --key or --key-file")


def recover(args: argparse.Namespace) -> int:
    require_lab_ack(args)
    target = resolve_target(args.target)
    state = load_state(target)
    if state.get("status") != "encrypted":
        raise SystemExit("target is not marked encrypted")

    key = read_key(args)
    recovered = 0
    for encrypted_path in iter_encrypted_files(target):
        blob = base64.b64decode(encrypted_path.read_bytes())
        nonce, ciphertext = blob[:16], blob[16:]
        plaintext = transform(ciphertext, key, nonce)
        plain_name = encrypted_path.name[: -len(ENCRYPTED_SUFFIX)]
        plain_path = encrypted_path.with_name(plain_name)
        plain_path.write_bytes(plaintext)
        encrypted_path.unlink()
        recovered += 1

    state["status"] = "recovered"
    state["recovered_at"] = time.time()
    state["recovered_count"] = recovered
    save_state(target, state)
    ransom_note = target / RANSOM_NOTE
    if ransom_note.exists():
        ransom_note.unlink()
    print(f"recovered_files={recovered}")
    return 0


def status(args: argparse.Namespace) -> int:
    target = resolve_target(args.target)
    state = load_state(target)
    plain_count = sum(1 for _ in iter_plain_files(target)) if target.exists() else 0
    encrypted_count = sum(1 for _ in iter_encrypted_files(target)) if target.exists() else 0
    report = {
        "target": str(target),
        "state": state or {"status": "not_encrypted"},
        "plain_files": plain_count,
        "encrypted_files_present": encrypted_count,
        "ransom_note_present": (target / RANSOM_NOTE).exists(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe ransomware simulator for SEED Emulator labs.")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-sample-files", help="create fake victim files")
    create.add_argument("--target", default="./import_folder")
    create.add_argument("--force", action="store_true")
    create.set_defaults(func=create_sample_files)

    enc = sub.add_parser("encrypt", help="simulate ransomware encryption")
    enc.add_argument("--target", default="./import_folder")
    enc.add_argument("--victim-id")
    enc.add_argument("--key-store", default=DEFAULT_KEY_STORE)
    enc.add_argument("--visible-key-file", default=DEFAULT_VISIBLE_KEY)
    enc.add_argument("--max-file-size", type=int, default=MAX_FILE_SIZE)
    enc.add_argument("--max-total-bytes", type=int, default=MAX_TOTAL_BYTES)
    enc.add_argument("--i-understand-this-is-a-lab", action="store_true")
    enc.set_defaults(func=encrypt)

    rec = sub.add_parser("recover", help="recover encrypted lab files")
    rec.add_argument("--target", default="./import_folder")
    rec.add_argument("--key")
    rec.add_argument("--key-file")
    rec.add_argument("--i-understand-this-is-a-lab", action="store_true")
    rec.set_defaults(func=recover)

    stat = sub.add_parser("status", help="show lab ransomware status")
    stat.add_argument("--target", default="./import_folder")
    stat.set_defaults(func=status)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
