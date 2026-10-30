#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
B00_DIR = REPO_ROOT / "examples" / "internet" / "B00_mini_internet"
B01_DIR = REPO_ROOT / "examples" / "internet" / "B01_dns_component"

for path in [REPO_ROOT, B00_DIR, B01_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mini_internet import build_emulator
from dns_component import run as build_dns_component
from seedemu.compiler import Docker, Platform
from seedemu.core import Action, Binding, Emulator, Filter, Node
from seedemu.layers import Base
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.services import DomainNameCachingService, DomainNameService
from seedemu.services.DomainNameCachingService import DomainNameCachingServer


STUB_ASES = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
LAB_DIR = "/opt/wannacry-lab"
IMPORT_DIR = "/home/seed/import_folder"
VULNERABLE_PORT = 445


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Y04 WannaCry simulator example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument(
        "--hosts-per-as",
        type=int,
        default=4,
        help="number of hosts to create in each B00 stub AS",
    )
    parser.add_argument("--vulnerable-port", type=int, default=VULNERABLE_PORT)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    if args.hosts_per_as < 1 or args.hosts_per_as > 180:
        parser.error("--hosts-per-as must be between 1 and 180")
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def install_file(node: Node, local_name: str, remote_name: str) -> None:
    content = (SCRIPT_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{LAB_DIR}/{remote_name}", content)


def prepare_lab_dir(node: Node) -> None:
    node.addBuildCommand(f"mkdir -p {LAB_DIR}")
    node.appendStartCommand(f"mkdir -p {LAB_DIR} {IMPORT_DIR}")


def target_addresses(hosts_per_as: int) -> list[str]:
    addresses = []
    for asn in STUB_ASES:
        for index in range(hosts_per_as):
            addresses.append(f"10.{asn}.0.{71 + index}")
    return addresses


def install_vulnerable_program(node: Node, port: int, targets_file_content: str) -> None:
    node.addSoftware("python3")
    prepare_lab_dir(node)
    install_file(node, "safe_ransomware_sim.py", "safe_ransomware_sim.py")
    install_file(node, "decrypt_files.py", "decrypt_files.py")
    install_file(node, "vulnerable_smb_service.py", "vulnerable_smb_service.py")
    install_file(node, "wannacry_worm.py", "wannacry_worm.py")
    install_file(node, "trigger_initial_infection.py", "trigger_initial_infection.py")
    node.setFile(f"{LAB_DIR}/targets.txt", targets_file_content)
    node.appendStartCommand(
        f"chmod +x {LAB_DIR}/safe_ransomware_sim.py {LAB_DIR}/decrypt_files.py {LAB_DIR}/vulnerable_smb_service.py {LAB_DIR}/wannacry_worm.py {LAB_DIR}/trigger_initial_infection.py"
    )
    node.appendStartCommand(
        f"python3 {LAB_DIR}/safe_ransomware_sim.py create-sample-files --target {IMPORT_DIR}"
    )
    node.appendStartCommand(
        "python3 {}/vulnerable_smb_service.py --port {} --target {} "
        ">> /var/log/wannacry-lab-vulnerable-service.log 2>&1".format(
            LAB_DIR,
            port,
            IMPORT_DIR,
        ),
        fork=True,
    )
    node.appendClassName("WannaCryLabVulnerableHost")


def install_blockchain_placeholder(emu: Emulator) -> None:
    """Placeholder for the later payment/key-release blockchain workflow."""
    return


def add_dns_to_base(base_emu: Emulator) -> Emulator:
    dns_component_file = SCRIPT_DIR / "dns_component.bin"
    build_dns_component(dumpfile=str(dns_component_file))

    dns_emu = Emulator()
    dns_emu.load(str(dns_component_file))
    emu = base_emu.merge(dns_emu, DEFAULT_MERGERS)

    emu.addBinding(Binding("a-root-server", filter=Filter(asn=171), action=Action.FIRST))
    emu.addBinding(Binding("b-root-server", filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding("a-com-server", filter=Filter(asn=151), action=Action.FIRST))
    emu.addBinding(Binding("b-com-server", filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding("a-net-server", filter=Filter(asn=152), action=Action.FIRST))
    emu.addBinding(Binding("a-edu-server", filter=Filter(asn=153), action=Action.FIRST))
    emu.addBinding(Binding("ns-twitter-com", filter=Filter(asn=161), action=Action.FIRST))
    emu.addBinding(Binding("ns-google-com", filter=Filter(asn=162), action=Action.FIRST))
    emu.addBinding(Binding("ns-example-net", filter=Filter(asn=163), action=Action.FIRST))
    emu.addBinding(Binding("ns-syr-edu", filter=Filter(asn=164), action=Action.FIRST))

    ldns = DomainNameCachingService()
    global_dns_1: DomainNameCachingServer = ldns.install("global-dns-1")
    global_dns_2: DomainNameCachingServer = ldns.install("global-dns-2")

    emu.getVirtualNode("global-dns-1").setDisplayName("Global DNS-1")
    emu.getVirtualNode("global-dns-2").setDisplayName("Global DNS-2")

    base: Base = emu.getLayer("Base")
    base.getAutonomousSystem(152).createHost("local-dns-1").joinNetwork("net0", address="10.152.0.53")
    base.getAutonomousSystem(153).createHost("local-dns-2").joinNetwork("net0", address="10.153.0.53")

    emu.addBinding(Binding("global-dns-1", filter=Filter(asn=152, nodeName="local-dns-1")))
    emu.addBinding(Binding("global-dns-2", filter=Filter(asn=153, nodeName="local-dns-2")))

    global_dns_1.setNameServerOnNodesByAsns(asns=[160, 170])
    global_dns_2.setNameServerOnAllNodes()

    dns: DomainNameService = emu.getLayer("DomainNameService")
    dns.getZone("example.net.").addRecord("www A 1.1.1.20")

    emu.addLayer(ldns)
    return emu


def customize_for_wannacry(emu: Emulator, hosts_per_as: int, vulnerable_port: int) -> None:
    base = emu.getLayer("Base")
    targets_file_content = "\n".join(target_addresses(hosts_per_as)) + "\n"
    for asn in STUB_ASES:
        current_as = base.getAutonomousSystem(asn)
        for index in range(hosts_per_as):
            install_vulnerable_program(
                current_as.getHost(f"host_{index}"),
                vulnerable_port,
                targets_file_content,
            )

    install_blockchain_placeholder(emu)


def build_y04_emulator(hosts_per_as: int, vulnerable_port: int) -> Emulator:
    base_emu = build_emulator(hosts_per_as=hosts_per_as)
    emu = add_dns_to_base(base_emu)
    customize_for_wannacry(emu, hosts_per_as=hosts_per_as, vulnerable_port=vulnerable_port)
    return emu


def run(
    dumpfile=None,
    hosts_per_as=4,
    vulnerable_port=VULNERABLE_PORT,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
) -> None:
    emu = build_y04_emulator(hosts_per_as=hosts_per_as, vulnerable_port=vulnerable_port)
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
        vulnerable_port=args.vulnerable_port,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
