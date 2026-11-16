#!/usr/bin/env python3
"""Apply and remove runtime egress bandwidth limits with Linux tc."""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import sys


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result


def find_interface(interface: str | None, subnet: str | None) -> str:
    if interface:
        return interface

    assert subnet is not None
    target = ipaddress.ip_network(subnet, strict=False)
    links = json.loads(run(["ip", "-j", "-4", "addr", "show"]).stdout)
    matches = []
    for link in links:
        for address in link.get("addr_info", []):
            local = address.get("local")
            if local and ipaddress.ip_address(local) in target:
                matches.append(link["ifname"])
                break
    if len(matches) != 1:
        raise RuntimeError(
            f"subnet {target} matched {len(matches)} interfaces: {', '.join(matches) or 'none'}"
        )
    return matches[0]


def add_target(parser: argparse.ArgumentParser) -> None:
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--interface", help="interface name, such as eth0")
    target.add_argument("--subnet", help="select the interface whose address belongs to this subnet")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or change an interface's runtime egress bandwidth limit."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    set_parser = commands.add_parser("set", help="replace the root qdisc with a TBF limiter")
    add_target(set_parser)
    set_parser.add_argument("--rate", required=True, help="tc rate, for example 5mbit")
    set_parser.add_argument("--burst", default="64kb", help="TBF burst size")
    set_parser.add_argument(
        "--queue-latency",
        default="100ms",
        help="maximum TBF queueing latency; this does not add artificial delay",
    )

    status_parser = commands.add_parser("status", help="show qdisc statistics")
    add_target(status_parser)

    clear_parser = commands.add_parser("clear", help="remove the runtime root qdisc")
    add_target(clear_parser)

    args = parser.parse_args()
    try:
        interface = find_interface(args.interface, args.subnet)
        if args.command == "set":
            run(
                [
                    "tc",
                    "qdisc",
                    "replace",
                    "dev",
                    interface,
                    "root",
                    "handle",
                    "1:",
                    "tbf",
                    "rate",
                    args.rate,
                    "burst",
                    args.burst,
                    "latency",
                    args.queue_latency,
                ]
            )
            print(
                f"limited {interface}: rate={args.rate} burst={args.burst} "
                f"queue_latency={args.queue_latency}"
            )
        elif args.command == "clear":
            result = run(["tc", "qdisc", "del", "dev", interface, "root"], check=False)
            if result.returncode != 0 and "No such file" not in result.stderr:
                raise RuntimeError(result.stderr.strip() or "could not remove root qdisc")
            print(f"cleared runtime limit on {interface}")
        else:
            print(run(["tc", "-s", "qdisc", "show", "dev", interface]).stdout, end="")
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"network control error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
