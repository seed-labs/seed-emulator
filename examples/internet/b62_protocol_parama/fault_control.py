#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_COMPOSE_FILE = SCRIPT_DIR / "output" / "docker-compose.yml"
SEED_ASN_LABEL = "org.seedsecuritylabs.seedemu.meta.asn"


def docker_compose_command() -> List[str]:
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return ["docker", "compose"]
    except FileNotFoundError:
        pass
    return ["docker-compose"]


def parse_container_names(values: Iterable[str]) -> List[str]:
    names: List[str] = []
    for value in values:
        for item in str(value).split(","):
            item = item.strip()
            if item:
                names.append(item)
    return names


def load_services(compose_file: Path) -> List[str]:
    with compose_file.open("r", encoding="utf-8") as handle:
        compose = yaml.safe_load(handle) or {}
    names: List[str] = []
    for name, service in compose.get("services", {}).items():
        labels = service.get("labels", {}) or {}
        if SEED_ASN_LABEL in labels:
            names.append(str(name))
    return sorted(names)


def validate_services(compose_file: Path, containers: Sequence[str]) -> None:
    services = set(load_services(compose_file))
    missing = [name for name in containers if name not in services]
    if missing:
        raise SystemExit(
            "unknown compose service(s): {}. Run `list` to inspect valid names.".format(
                ", ".join(missing)
            )
        )


def run_compose(compose_file: Path, args: Sequence[str]) -> int:
    cmd = docker_compose_command() + ["-f", str(compose_file)] + list(args)
    print("running: {}".format(" ".join(cmd)))
    result = subprocess.run(
        cmd,
        cwd=str(compose_file.parent),
        text=True,
        check=False,
    )
    return int(result.returncode)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stop or recover B62 protocol-parameter example containers."
    )
    parser.add_argument("action", choices=["down", "up", "list", "status"])
    parser.add_argument(
        "--compose",
        type=Path,
        default=DEFAULT_COMPOSE_FILE,
        help="Path to docker-compose.yml. Defaults to this example's output directory.",
    )
    parser.add_argument(
        "--container",
        nargs="*",
        default=[],
        help="One or more Compose services. Comma-separated and space-separated forms are both supported.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    compose_file = args.compose.resolve()
    if not compose_file.exists():
        raise SystemExit("compose file not found: {}".format(compose_file))

    if args.action == "list":
        for service in load_services(compose_file):
            print(service)
        return 0

    containers = parse_container_names(args.container)
    if not containers:
        raise SystemExit("--container is required for `{}`".format(args.action))
    validate_services(compose_file, containers)

    if args.action == "down":
        return run_compose(compose_file, ["stop"] + containers)
    if args.action == "up":
        return run_compose(compose_file, ["up", "-d", "--no-deps"] + containers)
    return run_compose(compose_file, ["ps"] + containers)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
