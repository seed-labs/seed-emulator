#!/usr/bin/env python3
"""Host-side monitor for the Y04 WannaCry lab.

Run this script on the Docker host. It discovers SEED Emulator host containers
from docker-compose labels, queries each import_folder state, and prints a live
summary of infection and recovery progress.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Optional


ASN_LABEL = "org.seedsecuritylabs.seedemu.meta.asn"
NODE_LABEL = "org.seedsecuritylabs.seedemu.meta.nodename"
ADDRESS_LABEL = "org.seedsecuritylabs.seedemu.meta.net.0.address"
TARGET = "/home/seed/import_folder"
KEY_FILE = "/tmp/wannacry_lab_decryption_key.txt"


def docker_compose_command() -> List[str]:
    docker = shutil.which("docker")
    if docker is not None:
        result = subprocess.run([docker, "compose", "version"], text=True, capture_output=True, check=False)
        if result.returncode == 0:
            return [docker, "compose"]

    docker_compose = shutil.which("docker-compose")
    if docker_compose is not None:
        return [docker_compose]

    return ["docker", "compose"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor the Y04 WannaCry lab from the Docker host.")
    parser.add_argument(
        "--compose-file",
        default=str(Path(__file__).resolve().parent / "output" / "docker-compose.yml"),
        help="path to generated docker-compose.yml",
    )
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between refreshes")
    parser.add_argument("--once", action="store_true", help="print one snapshot and exit")
    parser.add_argument("--no-clear", action="store_true", help="do not clear the terminal between refreshes")
    parser.add_argument("--show-hosts", type=int, default=20, help="max infected/recovered hosts to list")
    return parser.parse_args()


def load_compose_as_json(compose_file: Path) -> Dict[str, object]:
    result = subprocess.run(
        docker_compose_command() + ["-f", str(compose_file), "config", "--format", "json"],
        cwd=str(compose_file.parent),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker compose config failed")
    return json.loads(result.stdout)


def load_compose_with_simple_parser(compose_file: Path) -> Dict[str, object]:
    """Parse the small subset of Compose YAML needed for SEED labels.

    This fallback avoids a PyYAML dependency for the host-side monitor. It is not
    a general YAML parser; it only extracts service labels from generated compose
    files when Docker Compose JSON output is unavailable.
    """
    services: Dict[str, Dict[str, object]] = {}
    current_service: Optional[str] = None
    in_services = False
    in_labels = False

    for raw_line in compose_file.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            in_services = line == "services:"
            current_service = None
            in_labels = False
            continue

        if not in_services:
            continue

        if indent == 2 and line.endswith(":"):
            current_service = line[:-1]
            services[current_service] = {"labels": {}}
            in_labels = False
            continue

        if current_service is None:
            continue

        if indent == 4:
            in_labels = line == "labels:"
            continue

        if in_labels and indent >= 6:
            label_line = line[2:].strip() if line.startswith("- ") else line
            if ":" in label_line:
                key, value = label_line.split(":", 1)
            elif "=" in label_line:
                key, value = label_line.split("=", 1)
            else:
                continue
            key = key.strip().strip("'\"")
            value = value.strip().strip("'\"")
            services[current_service]["labels"][key] = value

    return {"services": services}


def load_compose(compose_file: Path) -> Dict[str, object]:
    try:
        return load_compose_as_json(compose_file)
    except Exception:
        return load_compose_with_simple_parser(compose_file)


def load_host_services(compose_file: Path) -> List[Dict[str, str]]:
    compose = load_compose(compose_file)

    hosts = []
    for service_name, service in compose.get("services", {}).items():
        labels = service.get("labels", {})
        node_name = str(labels.get(NODE_LABEL, ""))
        asn = str(labels.get(ASN_LABEL, ""))
        if not node_name.startswith("host_"):
            continue
        address = str(labels.get(ADDRESS_LABEL, "")).split("/", 1)[0]
        hosts.append(
            {
                "service": str(service_name),
                "asn": asn,
                "node": node_name,
                "address": address,
            }
        )

    return sorted(hosts, key=lambda item: (int(item["asn"]), item["node"]))


def compose_exec(compose_file: Path, service: str, command: str, timeout: int = 8) -> subprocess.CompletedProcess:
    return subprocess.run(
        docker_compose_command() + ["-f", str(compose_file), "exec", "-T", service, "sh", "-lc", command],
        cwd=str(compose_file.parent),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def key_fingerprint(key_text: str) -> str:
    key_text = key_text.strip()
    if not key_text:
        return ""
    return hashlib.sha256(key_text.encode()).hexdigest()[:12]


def query_host(compose_file: Path, host: Dict[str, str]) -> Dict[str, object]:
    command = (
        "python3 /opt/wannacry-lab/safe_ransomware_sim.py status --target {target}; "
        "printf '\\n---KEY---\\n'; "
        "if [ -s {key} ]; then cat {key}; fi"
    ).format(target=TARGET, key=KEY_FILE)
    result = compose_exec(compose_file, host["service"], command)

    item: Dict[str, object] = dict(host)
    item["reachable"] = result.returncode == 0
    item["error"] = result.stderr[-300:] if result.returncode != 0 else ""
    item["status"] = "unknown"
    item["encrypted_count"] = 0
    item["plain_files"] = 0
    item["victim_id"] = ""
    item["key_fingerprint"] = ""

    if result.returncode != 0:
        return item

    status_text, _, key_text = result.stdout.partition("\n---KEY---\n")
    try:
        report = json.loads(status_text)
    except json.JSONDecodeError as exc:
        item["error"] = f"could not parse status json: {exc}"
        return item

    state = report.get("state", {})
    item["status"] = state.get("status", "not_encrypted")
    item["encrypted_count"] = int(state.get("encrypted_count") or state.get("recovered_count") or 0)
    item["plain_files"] = int(report.get("plain_files") or 0)
    item["ransom_note_present"] = bool(report.get("ransom_note_present"))
    item["victim_id"] = str(state.get("victim_id", ""))
    item["key_fingerprint"] = key_fingerprint(key_text)
    return item


def summarize(items: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(items)
    reachable = sum(1 for item in items if item["reachable"])
    encrypted = [item for item in items if item["status"] == "encrypted"]
    recovered = [item for item in items if item["status"] == "recovered"]
    clean = [item for item in items if item["status"] == "not_encrypted"]
    failed = [item for item in items if not item["reachable"] or item["status"] == "unknown"]

    fingerprints = [str(item["key_fingerprint"]) for item in encrypted + recovered if item["key_fingerprint"]]
    duplicate_fingerprints = sorted({fp for fp in fingerprints if fingerprints.count(fp) > 1})

    return {
        "total": total,
        "reachable": reachable,
        "encrypted": encrypted,
        "recovered": recovered,
        "clean": clean,
        "failed": failed,
        "unique_key_fingerprints": len(set(fingerprints)),
        "key_fingerprint_count": len(fingerprints),
        "duplicate_fingerprints": duplicate_fingerprints,
    }


def render(items: List[Dict[str, object]], args: argparse.Namespace) -> None:
    summary = summarize(items)
    if not args.no_clear:
        os.system("cls" if os.name == "nt" else "clear")

    print("Y04 WANNACRY LAB MONITOR")
    print("========================")
    print(f"hosts discovered          : {summary['total']}")
    print(f"hosts reachable           : {summary['reachable']}")
    print(f"encrypted hosts           : {len(summary['encrypted'])}")
    print(f"recovered hosts           : {len(summary['recovered'])}")
    print(f"clean hosts               : {len(summary['clean'])}")
    print(f"unknown/unreachable hosts : {len(summary['failed'])}")
    print(
        "key fingerprints          : {}/{} unique".format(
            summary["unique_key_fingerprints"],
            summary["key_fingerprint_count"],
        )
    )
    if summary["duplicate_fingerprints"]:
        print("duplicate key fingerprints: {}".format(", ".join(summary["duplicate_fingerprints"])))
    else:
        print("duplicate key fingerprints: none observed")
    print()

    def print_table(title: str, rows: List[Dict[str, object]]) -> None:
        print(title)
        print("-" * len(title))
        if not rows:
            print("(none)")
            print()
            return
        for item in rows[: args.show_hosts]:
            print(
                "AS{asn:<3} {node:<8} {address:<13} {status:<10} files={files:<2} victim={victim:<16} keyfp={keyfp}".format(
                    asn=item["asn"],
                    node=item["node"],
                    address=item["address"],
                    status=item["status"],
                    files=item["encrypted_count"],
                    victim=item["victim_id"] or "-",
                    keyfp=item["key_fingerprint"] or "-",
                )
            )
        if len(rows) > args.show_hosts:
            print(f"... {len(rows) - args.show_hosts} more")
        print()

    print_table("Encrypted Hosts", summary["encrypted"])
    print_table("Recovered Hosts", summary["recovered"])
    print_table("Clean Hosts", summary["clean"])
    print("Press Ctrl-C to stop.")


def main() -> int:
    args = parse_args()
    compose_file = Path(args.compose_file).resolve()
    if not compose_file.exists():
        raise SystemExit(f"compose file not found: {compose_file}")

    hosts = load_host_services(compose_file)
    if not hosts:
        raise SystemExit(f"no host services found in {compose_file}")

    while True:
        items = [query_host(compose_file, host) for host in hosts]
        render(items, args)
        if args.once:
            break
        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
