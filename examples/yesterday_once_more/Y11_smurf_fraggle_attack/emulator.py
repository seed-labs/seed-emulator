#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
B00_DIR = REPO_ROOT / "examples" / "internet" / "B00_mini_internet"
TRAFFIC_VISUALIZER_SOURCE_DIR = REPO_ROOT / "tools" / "TrafficVisualizer"

for path in [REPO_ROOT, B00_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mini_internet import build_emulator
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Node


ATTACKER_HOST = (150, "host_0")
VICTIM_HOST = (151, "host_0")
VICTIM_ROUTER = (151, "router0")
LEGITIMATE_CLIENT_HOST = (153, "host_0")
TARGET_ASN = 152
TARGET_ROUTER = "router0"
TARGET_NETWORK = "net0"
TARGET_NETWORK_PREFIX = "10.152.0"
AUTO_HOST_START = 71
FIRST_USABLE_HOST = 2
LAST_USABLE_HOST = 253
MAX_TARGET_HOSTS = LAST_USABLE_HOST - FIRST_USABLE_HOST + 1
SMURF_DIR = "/opt/demo"
TRAFFIC_VISUALIZER_DIR = f"{SMURF_DIR}/traffic_visualizer"
TRAFFIC_VISUALIZER_HOST_PORT = 8081
TRAFFIC_VISUALIZER_CONTAINER_PORT = 8080
FRAGGLE_PORT = 19
VICTIM_SERVICE_PORT = 8000
HEALTH_PROBE_HOST_PORT = 8082
HEALTH_PROBE_CONTAINER_PORT = 8080


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Y11 Smurf attack example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument(
        "--target-hosts",
        type=int,
        default=12,
        help=f"number of hosts on the vulnerable AS152 broadcast LAN (maximum: {MAX_TARGET_HOSTS})",
    )
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def get_base(emu: Emulator):
    return emu.getLayer("Base")


def get_host(emu: Emulator, asn: int, name: str) -> Node:
    return get_base(emu).getAutonomousSystem(asn).getHost(name)


def get_router(emu: Emulator, asn: int, name: str) -> Node:
    return get_base(emu).getAutonomousSystem(asn).getRouter(name)


def install_file(node: Node, local_name: str, remote_name: str) -> None:
    content = (SCRIPT_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{SMURF_DIR}/{remote_name}", content)


def install_traffic_visualizer_file(node: Node, local_name: str) -> None:
    content = (TRAFFIC_VISUALIZER_SOURCE_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{TRAFFIC_VISUALIZER_DIR}/{local_name}", content)


def prepare_smurf_dir(node: Node) -> None:
    node.addBuildCommand(f"mkdir -p {SMURF_DIR}")
    node.appendStartCommand(f"mkdir -p {SMURF_DIR}")


def get_manual_target_addresses(hosts_per_as: int) -> list[str]:
    """Return free AS152 host addresses in deterministic allocation order."""
    first_address_after_b00_hosts = AUTO_HOST_START + max(hosts_per_as, 0)
    offsets = list(range(first_address_after_b00_hosts, LAST_USABLE_HOST + 1))
    offsets.extend(range(FIRST_USABLE_HOST, AUTO_HOST_START))
    return [f"{TARGET_NETWORK_PREFIX}.{offset}" for offset in offsets]


def add_target_hosts(emu: Emulator, target_hosts: int, hosts_per_as: int) -> None:
    target_as = get_base(emu).getAutonomousSystem(TARGET_ASN)
    existing = max(hosts_per_as, 0)
    addresses = get_manual_target_addresses(existing)
    requested_new_hosts = target_hosts - existing
    if requested_new_hosts > len(addresses):
        raise ValueError(
            f"--target-hosts cannot exceed {MAX_TARGET_HOSTS} on the AS152 /24 network"
        )

    for index in range(existing, target_hosts):
        address = addresses[index - existing]
        target_as.createHost(f"host_{index}").joinNetwork(TARGET_NETWORK, address=address)


def configure_directed_broadcast_router(router: Node) -> None:
    router.appendStartCommand("sysctl -w net.ipv4.ip_forward=1")
    router.appendStartCommand("sysctl -w net.ipv4.conf.all.bc_forwarding=1 || true")
    router.appendStartCommand("sysctl -w net.ipv4.conf.default.bc_forwarding=1 || true")
    router.appendStartCommand(
        "for f in /proc/sys/net/ipv4/conf/*/bc_forwarding; do [ -e \"$f\" ] && echo 1 > \"$f\"; done"
    )
    router.appendStartCommand("sysctl -w net.ipv4.conf.all.rp_filter=0")
    router.appendStartCommand("sysctl -w net.ipv4.conf.default.rp_filter=0")
    router.appendClassName("SmurfDirectedBroadcastRouter")
    router.setDisplayName("Directed-Broadcast-Router")


def configure_victim_access_router(router: Node) -> None:
    router.addSoftware("python3")
    router.addSoftware("iproute2")
    prepare_smurf_dir(router)
    install_traffic_visualizer_file(router, "network_control.py")
    router.appendStartCommand(f"chmod +x {TRAFFIC_VISUALIZER_DIR}/network_control.py")
    router.appendClassName("VictimAccessLinkController")
    router.setDisplayName("Victim-Access-Router")


def configure_target_host(host: Node) -> None:
    host.addSoftware("python3")
    prepare_smurf_dir(host)
    install_file(host, "fraggle_amplifier.py", "fraggle_amplifier.py")
    host.appendStartCommand("sysctl -w net.ipv4.icmp_echo_ignore_broadcasts=0")
    host.appendStartCommand("sysctl -w net.ipv4.conf.all.rp_filter=0")
    host.appendStartCommand("sysctl -w net.ipv4.conf.default.rp_filter=0")
    host.appendStartCommand(f"chmod +x {SMURF_DIR}/fraggle_amplifier.py")
    host.appendStartCommand(
        "python3 {}/fraggle_amplifier.py --port {} --mode chargen --response-size 512 "
        ">> /var/log/fraggle-amplifier-supervisor.log 2>&1".format(SMURF_DIR, FRAGGLE_PORT),
        fork=True,
    )
    host.appendClassName("SmurfAmplifierHost")
    host.appendClassName("FraggleAmplifierHost")


def configure_attacker(host: Node) -> None:
    host.addSoftware("python3")
    prepare_smurf_dir(host)
    install_file(host, "smurf_attack.py", "smurf_attack.py")
    install_file(host, "fraggle_attack.py", "fraggle_attack.py")
    install_file(host, "trigger_attack.sh", "trigger_attack.sh")
    host.appendStartCommand(
        f"chmod +x {SMURF_DIR}/smurf_attack.py {SMURF_DIR}/fraggle_attack.py {SMURF_DIR}/trigger_attack.sh"
    )
    host.appendClassName("SmurfAttacker")
    host.appendClassName("FraggleAttacker")
    host.setDisplayName("Attacker")


def configure_victim(host: Node) -> None:
    host.addSoftware("python3")
    host.addSoftware("tcpdump")
    prepare_smurf_dir(host)
    install_traffic_visualizer_file(host, "victim_http_service.py")
    install_traffic_visualizer_file(host, "traffic_visualizer.py")
    install_traffic_visualizer_file(host, "dashboard.html")
    install_file(host, "traffic_visualizer_config.json", "traffic_visualizer/config.json")
    install_file(
        host,
        "traffic_visualizer_extension.js",
        "traffic_visualizer/traffic_visualizer_extension.js",
    )
    install_file(
        host,
        "traffic_visualizer_extension.css",
        "traffic_visualizer/traffic_visualizer_extension.css",
    )
    host.addPortForwarding(TRAFFIC_VISUALIZER_HOST_PORT, TRAFFIC_VISUALIZER_CONTAINER_PORT)
    host.appendStartCommand(f"mkdir -p {TRAFFIC_VISUALIZER_DIR}")
    host.appendStartCommand(
        f"chmod +x {TRAFFIC_VISUALIZER_DIR}/victim_http_service.py "
        f"{TRAFFIC_VISUALIZER_DIR}/traffic_visualizer.py"
    )
    host.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/victim_http_service.py --port {VICTIM_SERVICE_PORT} "
        ">> /var/log/victim-http-service.log 2>&1",
        fork=True,
    )
    host.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/traffic_visualizer.py "
        f"--config {TRAFFIC_VISUALIZER_DIR}/config.json "
        f"--dashboard {TRAFFIC_VISUALIZER_DIR}/dashboard.html "
        ">> /var/log/traffic-visualizer.log 2>&1",
        fork=True,
    )
    host.appendClassName("SmurfVictim")
    host.appendClassName("FraggleVictim")
    host.appendClassName("TrafficVisualizer")
    host.appendClassName("VictimHttpService")
    host.setDisplayName("Victim")


def configure_legitimate_client(host: Node) -> None:
    host.addSoftware("python3")
    prepare_smurf_dir(host)
    install_traffic_visualizer_file(host, "health_probe.py")
    host.addPortForwarding(HEALTH_PROBE_HOST_PORT, HEALTH_PROBE_CONTAINER_PORT)
    host.appendStartCommand(f"chmod +x {TRAFFIC_VISUALIZER_DIR}/health_probe.py")
    host.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/health_probe.py "
        f"--target http://10.151.0.71:{VICTIM_SERVICE_PORT}/health "
        f"--bandwidth-url http://10.151.0.71:{VICTIM_SERVICE_PORT}/bandwidth "
        "--interval 0.2 --timeout 0.5 "
        "--bandwidth-bytes 262144 --bandwidth-interval 5 --bandwidth-timeout 3 "
        f"--serve-port {HEALTH_PROBE_CONTAINER_PORT} --cors-origin '*' --max-samples 300 "
        ">> /var/log/victim-health-probe.log 2>&1",
        fork=True,
    )
    host.appendClassName("LegitimateClient")
    host.setDisplayName("Legitimate-Client")


def customize_b00_for_smurf(emu: Emulator, target_hosts: int, hosts_per_as: int) -> None:
    if target_hosts < hosts_per_as:
        raise ValueError("--target-hosts must be greater than or equal to --hosts-per-as")

    add_target_hosts(emu, target_hosts=target_hosts, hosts_per_as=hosts_per_as)
    configure_directed_broadcast_router(get_router(emu, TARGET_ASN, TARGET_ROUTER))
    configure_victim_access_router(get_router(emu, *VICTIM_ROUTER))
    configure_attacker(get_host(emu, *ATTACKER_HOST))
    configure_victim(get_host(emu, *VICTIM_HOST))
    configure_legitimate_client(get_host(emu, *LEGITIMATE_CLIENT_HOST))

    target_as = get_base(emu).getAutonomousSystem(TARGET_ASN)
    for index in range(target_hosts):
        configure_target_host(target_as.getHost(f"host_{index}"))


def build_y11_emulator(hosts_per_as: int, target_hosts: int) -> Emulator:
    emu = build_emulator(hosts_per_as=hosts_per_as)
    customize_b00_for_smurf(emu, target_hosts=target_hosts, hosts_per_as=hosts_per_as)
    return emu


def run(
    dumpfile=None,
    hosts_per_as=2,
    target_hosts=12,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
) -> None:
    emu = build_y11_emulator(hosts_per_as=hosts_per_as, target_hosts=target_hosts)
    if dumpfile is not None:
        emu.dump(dumpfile)
        return

    if render:
        emu.render()

    docker = Docker(platform=platform)
    emu.compile(docker, output or "./output", override=override)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    run(
        dumpfile=args.dumpfile,
        hosts_per_as=args.hosts_per_as,
        target_hosts=args.target_hosts,
        output=str(output_dir),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
