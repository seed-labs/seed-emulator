#!/usr/bin/env python3
"""Host-side monitor for the Y05 SQL Slammer lab."""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="Monitor the Y05 SQL Slammer lab from the Docker host.")
    parser.add_argument("--compose-file", default=str(Path(__file__).resolve().parent / "output" / "docker-compose.yml"))
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-clear", action="store_true")
    parser.add_argument("--show-hosts", type=int, default=24)
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


def load_host_services(compose_file: Path) -> List[Dict[str, str]]:
    compose = load_compose_as_json(compose_file)
    hosts = []
    for service_name, service in compose.get("services", {}).items():
        labels = service.get("labels", {})
        node_name = str(labels.get(NODE_LABEL, ""))
        asn = str(labels.get(ASN_LABEL, ""))
        if not node_name.startswith("host_"):
            continue
        address = str(labels.get(ADDRESS_LABEL, "")).split("/", 1)[0]
        hosts.append({"service": str(service_name), "asn": asn, "node": node_name, "address": address})
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


def query_host(compose_file: Path, host: Dict[str, str]) -> Dict[str, object]:
    command = (
        "if [ -s /tmp/slammer_lab_status.json ]; then cat /tmp/slammer_lab_status.json; "
        "else printf '{\"status\":\"unknown\",\"infected\":false}'; fi; "
        "printf '\\n---LOG---\\n'; "
        "if [ -s /tmp/slammer_lab_worm.log ]; then tail -n 5 /tmp/slammer_lab_worm.log; fi"
    )
    result = compose_exec(compose_file, host["service"], command)
    item: Dict[str, object] = dict(host)
    item["reachable"] = result.returncode == 0
    item["status"] = "unknown"
    item["infected"] = False
    item["generation"] = ""
    item["duplicates"] = 0
    item["packets_sent"] = ""
    item["error"] = result.stderr[-300:] if result.returncode != 0 else ""

    if result.returncode != 0:
        return item

    status_text, _, log_text = result.stdout.partition("\n---LOG---\n")
    try:
        status = json.loads(status_text)
    except json.JSONDecodeError as exc:
        item["error"] = f"could not parse status json: {exc}"
        return item

    item["status"] = str(status.get("status", "unknown"))
    item["infected"] = bool(status.get("infected"))
    item["generation"] = status.get("generation", "")
    item["duplicates"] = int(status.get("duplicate_packets", 0) or 0)
    for line in reversed(log_text.splitlines()):
        if "finish packets_sent=" in line:
            item["packets_sent"] = line.rsplit("packets_sent=", 1)[-1]
            break
    return item


def render(items: List[Dict[str, object]], args: argparse.Namespace) -> None:
    if not args.no_clear:
        os.system("cls" if os.name == "nt" else "clear")
    infected = [item for item in items if item["infected"]]
    patched = [item for item in items if item["status"] == "patched"]
    clean = [item for item in items if item["status"] in {"listening", "unknown"} and not item["infected"]]
    unreachable = [item for item in items if not item["reachable"]]
    duplicate_packets = sum(int(item["duplicates"]) for item in items)

    print("Y05 SQL SLAMMER LAB MONITOR")
    print("===========================")
    print(f"hosts discovered          : {len(items)}")
    print(f"infected hosts            : {len(infected)}")
    print(f"patched hosts             : {len(patched)}")
    print(f"clean/unknown hosts       : {len(clean)}")
    print(f"unreachable hosts         : {len(unreachable)}")
    print(f"duplicate infection packets: {duplicate_packets}")
    print()

    print("Infected Hosts")
    print("--------------")
    if not infected:
        print("(none)")
    for item in infected[: args.show_hosts]:
        print(
            "AS{asn:<3} {node:<8} {address:<13} gen={gen:<3} dup={dup:<4} sent={sent}".format(
                asn=item["asn"],
                node=item["node"],
                address=item["address"],
                gen=item["generation"],
                dup=item["duplicates"],
                sent=item["packets_sent"] or "-",
            )
        )
    if len(infected) > args.show_hosts:
        print(f"... {len(infected) - args.show_hosts} more")
    print()
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
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
