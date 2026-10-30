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


AMPLIFIER_HOSTS = [(152, "host_0"), (160, "host_0"), (171, "host_0")]
ATTACKER_HOST = (150, "host_0")
VICTIM_HOST = (151, "host_0")
VICTIM_ROUTER = (151, "router0")
LEGITIMATE_CLIENT_HOST = (153, "host_0")
NTP_LIKE_DIR = "/opt/ntp-like"
TRAFFIC_VISUALIZER_DIR = f"{NTP_LIKE_DIR}/traffic_visualizer"
TRAFFIC_VISUALIZER_HOST_PORT = 8081
TRAFFIC_VISUALIZER_CONTAINER_PORT = 8080
VICTIM_LOG = "/var/log/ntp-like-victim.log"
VICTIM_SERVICE_PORT = 8000
HEALTH_PROBE_HOST_PORT = 8082
HEALTH_PROBE_CONTAINER_PORT = 8080


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Y10 NTP-like amplification example.")
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--hosts-per-as", type=int, default=2)
    parser.add_argument("--response-size", type=int, default=1200)
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def get_host(emu: Emulator, asn: int, name: str) -> Node:
    base = emu.getLayer("Base")
    return base.getAutonomousSystem(asn).getHost(name)


def get_router(emu: Emulator, asn: int, name: str) -> Node:
    base = emu.getLayer("Base")
    return base.getAutonomousSystem(asn).getRouter(name)


def install_file(node: Node, local_name: str, remote_name: str) -> None:
    content = (SCRIPT_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{NTP_LIKE_DIR}/{remote_name}", content)


def install_traffic_visualizer_file(node: Node, local_name: str) -> None:
    content = (TRAFFIC_VISUALIZER_SOURCE_DIR / local_name).read_text(encoding="utf-8")
    node.setFile(f"{TRAFFIC_VISUALIZER_DIR}/{local_name}", content)


def prepare_ntp_like_dir(node: Node) -> None:
    node.addBuildCommand(f"mkdir -p {NTP_LIKE_DIR}")
    node.appendStartCommand(f"mkdir -p {NTP_LIKE_DIR}")


def install_amplifier(node: Node, response_size: int) -> None:
    node.addSoftware("python3")
    prepare_ntp_like_dir(node)
    install_file(node, "ntp_like_daemon.py", "ntp_like_daemon.py")
    node.appendStartCommand(
        "python3 {}/ntp_like_daemon.py "
        "--port 123 "
        "--response-size {} "
        "--allowed-prefix 10. "
        "--reflect-token seedemu-lab "
        "--reflect-target-prefix 10. "
        ">> /var/log/ntp-like-daemon.log 2>&1".format(NTP_LIKE_DIR, response_size),
        fork=True,
    )
    node.appendClassName("NtpLikeAmplifier")


def install_attacker(node: Node) -> None:
    node.addSoftware("python3")
    prepare_ntp_like_dir(node)
    install_file(node, "trigger_attack.py", "trigger_attack.py")
    install_file(node, "trigger_attack.sh", "trigger_attack.sh")
    node.appendStartCommand(f"chmod +x {NTP_LIKE_DIR}/trigger_attack.py {NTP_LIKE_DIR}/trigger_attack.sh")
    node.appendClassName("NtpLikeAttacker")


def install_victim_access_router(node: Node) -> None:
    node.addSoftware("python3")
    node.addSoftware("iproute2")
    prepare_ntp_like_dir(node)
    install_traffic_visualizer_file(node, "network_control.py")
    node.appendStartCommand(f"chmod +x {TRAFFIC_VISUALIZER_DIR}/network_control.py")
    node.appendClassName("VictimAccessLinkController")


def install_victim(node: Node) -> None:
    node.addSoftware("python3")
    node.addSoftware("tcpdump")
    prepare_ntp_like_dir(node)
    install_file(node, "udp_sink.py", "udp_sink.py")
    install_traffic_visualizer_file(node, "victim_http_service.py")
    install_traffic_visualizer_file(node, "traffic_visualizer.py")
    install_traffic_visualizer_file(node, "dashboard.html")
    install_file(node, "traffic_visualizer_config.json", "traffic_visualizer/config.json")
    install_file(
        node,
        "traffic_visualizer_extension.js",
        "traffic_visualizer/traffic_visualizer_extension.js",
    )
    install_file(
        node,
        "traffic_visualizer_extension.css",
        "traffic_visualizer/traffic_visualizer_extension.css",
    )
    node.addPortForwarding(TRAFFIC_VISUALIZER_HOST_PORT, TRAFFIC_VISUALIZER_CONTAINER_PORT)
    node.appendStartCommand(f": > {VICTIM_LOG}")
    node.appendStartCommand(f"mkdir -p {TRAFFIC_VISUALIZER_DIR}")
    node.appendStartCommand(
        f"chmod +x {TRAFFIC_VISUALIZER_DIR}/victim_http_service.py "
        f"{TRAFFIC_VISUALIZER_DIR}/traffic_visualizer.py"
    )
    node.appendStartCommand(
        f"python3 {NTP_LIKE_DIR}/udp_sink.py --port 9000 --log {VICTIM_LOG} "
        ">> /var/log/ntp-like-victim-sink.log 2>&1",
        fork=True,
    )
    node.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/victim_http_service.py --port {VICTIM_SERVICE_PORT} "
        ">> /var/log/victim-http-service.log 2>&1",
        fork=True,
    )
    node.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/traffic_visualizer.py "
        f"--config {TRAFFIC_VISUALIZER_DIR}/config.json "
        f"--dashboard {TRAFFIC_VISUALIZER_DIR}/dashboard.html "
        ">> /var/log/traffic-visualizer.log 2>&1",
        fork=True,
    )
    node.appendClassName("NtpLikeVictim")
    node.appendClassName("TrafficVisualizer")
    node.appendClassName("VictimHttpService")


def install_legitimate_client(node: Node) -> None:
    node.addSoftware("python3")
    prepare_ntp_like_dir(node)
    install_traffic_visualizer_file(node, "health_probe.py")
    node.addPortForwarding(HEALTH_PROBE_HOST_PORT, HEALTH_PROBE_CONTAINER_PORT)
    node.appendStartCommand(f"chmod +x {TRAFFIC_VISUALIZER_DIR}/health_probe.py")
    node.appendStartCommand(
        f"python3 {TRAFFIC_VISUALIZER_DIR}/health_probe.py "
        f"--target http://10.151.0.71:{VICTIM_SERVICE_PORT}/health "
        f"--bandwidth-url http://10.151.0.71:{VICTIM_SERVICE_PORT}/bandwidth "
        "--interval 0.2 --timeout 0.5 "
        "--bandwidth-bytes 262144 --bandwidth-interval 5 --bandwidth-timeout 3 "
        f"--serve-port {HEALTH_PROBE_CONTAINER_PORT} --cors-origin '*' --max-samples 300 "
        ">> /var/log/victim-health-probe.log 2>&1",
        fork=True,
    )
    node.appendClassName("LegitimateClient")


def customize_b00_for_ntp_amplification(emu: Emulator, response_size: int) -> None:
    for asn, host in AMPLIFIER_HOSTS:
        install_amplifier(get_host(emu, asn, host), response_size)

    install_attacker(get_host(emu, *ATTACKER_HOST))
    install_victim_access_router(get_router(emu, *VICTIM_ROUTER))
    install_victim(get_host(emu, *VICTIM_HOST))
    install_legitimate_client(get_host(emu, *LEGITIMATE_CLIENT_HOST))


def build_y10_emulator(hosts_per_as: int, response_size: int) -> Emulator:
    emu = build_emulator(hosts_per_as=hosts_per_as)
    customize_b00_for_ntp_amplification(emu, response_size=response_size)
    return emu


def run(
    dumpfile=None,
    hosts_per_as=2,
    response_size=1200,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
) -> None:
    emu = build_y10_emulator(hosts_per_as=hosts_per_as, response_size=response_size)
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
        response_size=args.response_size,
        output=str(output_dir),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
