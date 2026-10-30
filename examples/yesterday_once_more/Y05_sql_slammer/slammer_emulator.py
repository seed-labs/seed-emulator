#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
B00_DIR = REPO_ROOT / "examples" / "internet" / "B00_mini_internet"

for path in [REPO_ROOT, B00_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mini_internet import build_emulator
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Node


STUB_ASES = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
LAB_DIR = "/opt/slammer-lab"
SLAMMER_PORT = 1434


def parse_asn_list(value: str) -> set[int]:
    if not value:
        return set()
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Y05 SQL Slammer simulator example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=4)
    parser.add_argument("--packet-rate", type=float, default=80.0)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--patched-asns", default="", help="comma-separated ASNs to mark patched")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    if args.hosts_per_as < 1 or args.hosts_per_as > 180:
        parser.error("--hosts-per-as must be between 1 and 180")
    args.patched_asns = parse_asn_list(args.patched_asns)
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def install_file(node: Node, local_name: str, remote_name: str) -> None:
    content = (SCRIPT_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{LAB_DIR}/{remote_name}", content)


def target_addresses(hosts_per_as: int) -> list[str]:
    addresses = []
    for asn in STUB_ASES:
        for index in range(hosts_per_as):
            addresses.append(f"10.{asn}.0.{71 + index}")
    return addresses


def install_slammer_host(
    node: Node,
    targets_file_content: str,
    patched: bool,
    packet_rate: float,
    duration: float,
) -> None:
    node.addSoftware("python3")
    node.addBuildCommand(f"mkdir -p {LAB_DIR}")
    node.appendStartCommand(f"mkdir -p {LAB_DIR}")
    for filename in [
        "slammer_packet.py",
        "slammer_service.py",
        "slammer_worm.py",
        "trigger_initial_infection.py",
    ]:
        install_file(node, filename, filename)
    node.setFile(f"{LAB_DIR}/targets.txt", targets_file_content)
    node.appendStartCommand(f"chmod +x {LAB_DIR}/*.py")
    patched_flag = " --patched" if patched else ""
    node.appendStartCommand(
        "python3 {}/slammer_service.py --port {} --packet-rate {} --duration {}{} "
        ">> /var/log/slammer-lab-service.log 2>&1".format(
            LAB_DIR,
            SLAMMER_PORT,
            packet_rate,
            duration,
            patched_flag,
        ),
        fork=True,
    )
    node.appendClassName("SqlSlammerLabPatchedHost" if patched else "SqlSlammerLabVulnerableHost")


def customize_for_slammer(
    emu: Emulator,
    hosts_per_as: int,
    patched_asns: set[int],
    packet_rate: float,
    duration: float,
) -> None:
    base = emu.getLayer("Base")
    targets_file_content = "\n".join(target_addresses(hosts_per_as)) + "\n"
    for asn in STUB_ASES:
        current_as = base.getAutonomousSystem(asn)
        for index in range(hosts_per_as):
            install_slammer_host(
                current_as.getHost(f"host_{index}"),
                targets_file_content,
                patched=asn in patched_asns,
                packet_rate=packet_rate,
                duration=duration,
            )


def build_y05_emulator(
    hosts_per_as: int,
    patched_asns: set[int],
    packet_rate: float,
    duration: float,
) -> Emulator:
    emu = build_emulator(hosts_per_as=hosts_per_as)
    customize_for_slammer(emu, hosts_per_as, patched_asns, packet_rate, duration)
    return emu


def run(
    dumpfile=None,
    hosts_per_as=4,
    patched_asns=None,
    packet_rate=80.0,
    duration=20.0,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
) -> None:
    emu = build_y05_emulator(hosts_per_as, patched_asns or set(), packet_rate, duration)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    emu.compile(Docker(platform=platform), str(output_dir), override=override)


def main() -> int:
    args = parse_args()
    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        patched_asns=args.patched_asns,
        packet_rate=args.packet_rate,
        duration=args.duration,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
