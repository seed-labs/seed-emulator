#!/usr/bin/env python3
"""Validate tagged macvlan connectivity between multi-host KVM guests.

The check runs after VM creation and before K3s installation. It creates one
temporary VLAN parent and macvlan interface per configured fabric trunk on a
deterministic VM pair, verifies bidirectional ICMP, and removes all temporary
interfaces before returning.
"""

from __future__ import annotations

import argparse
import ipaddress
import shlex
import subprocess
from pathlib import Path
from typing import Any

from manageMultiHostKvmConfig import expandPath, fabricVlanTrunks, hostList, loadYaml, vmPlan


def renderShellCommand(commands: list[list[str]]) -> str:
    """Return a fail-fast remote shell command from argv-style commands."""
    return "set -euo pipefail; " + "; ".join(
        " ".join(shlex.quote(part) for part in command)
        for command in commands
    )


def runSsh(
    *,
    user: str,
    key: str,
    ip: str,
    command: str,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run one command in a VM through the control host."""
    return subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "IdentityAgent=none",
            "-o",
            "ConnectTimeout=10",
            "-i",
            key,
            f"{user}@{ip}",
            command,
        ],
        check=check,
        text=True,
        capture_output=capture_output,
    )


def selectFirstNodeByHost(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the first deterministic VM on each hypervisor."""
    nodes = vmPlan(data)
    selected: list[dict[str, Any]] = []
    for host in hostList(data):
        node = next((item for item in nodes if item["hypervisor"] == host["name"]), None)
        if node is not None:
            selected.append(node)
    return selected


def createSetupCommands(
    *,
    master_interface: str,
    vlan_id: int,
    vlan_interface: str,
    macvlan_interface: str,
    address: str,
    mtu: int,
) -> list[list[str]]:
    """Return commands that create one temporary VLAN-backed macvlan."""
    return [
        ["sudo", "-n", "ip", "link", "set", master_interface, "up"],
        [
            "sudo",
            "-n",
            "ip",
            "link",
            "add",
            "link",
            master_interface,
            "name",
            vlan_interface,
            "type",
            "vlan",
            "id",
            str(vlan_id),
        ],
        ["sudo", "-n", "ip", "link", "set", vlan_interface, "up"],
        [
            "sudo",
            "-n",
            "ip",
            "link",
            "add",
            "link",
            vlan_interface,
            "name",
            macvlan_interface,
            "type",
            "macvlan",
            "mode",
            "bridge",
        ],
        ["sudo", "-n", "ip", "link", "set", macvlan_interface, "mtu", str(mtu)],
        ["sudo", "-n", "ip", "addr", "add", address, "dev", macvlan_interface],
        ["sudo", "-n", "ip", "link", "set", macvlan_interface, "up"],
    ]


def createCleanupCommand(vlan_interface: str, macvlan_interface: str) -> str:
    """Return an idempotent cleanup command for one temporary probe."""
    commands = [
        f"sudo -n ip link del {shlex.quote(macvlan_interface)} >/dev/null 2>&1 || true",
        f"sudo -n ip link del {shlex.quote(vlan_interface)} >/dev/null 2>&1 || true",
    ]
    return "; ".join(commands)


def probePair(
    *,
    user: str,
    key: str,
    left: dict[str, Any],
    right: dict[str, Any],
    trunk: dict[str, Any],
    test_index: int,
    ping_count: int,
    ping_timeout: int,
    mtu_payload_bytes: int,
) -> None:
    """Validate one trunk between two VMs."""
    base = int(ipaddress.ip_address("198.18.0.0")) + (test_index * 4)
    network = ipaddress.ip_network((base, 30))
    left_ip = str(network.network_address + 1)
    right_ip = str(network.network_address + 2)
    vlan_interface = f"pfv{test_index}"
    macvlan_interface = f"pfm{test_index}"
    vlan_id = int(trunk["vlanEnd"])
    master_interface = str(trunk["masterInterface"])

    cleanup = createCleanupCommand(vlan_interface, macvlan_interface)
    for node in (left, right):
        runSsh(user=user, key=key, ip=str(node["ip"]), command=cleanup)

    try:
        runSsh(
            user=user,
            key=key,
            ip=str(left["ip"]),
            command=renderShellCommand(
                createSetupCommands(
                    master_interface=master_interface,
                    vlan_id=vlan_id,
                    vlan_interface=vlan_interface,
                    macvlan_interface=macvlan_interface,
                    address=f"{left_ip}/30",
                    mtu=int(trunk["mtu"]),
                )
            ),
        )
        runSsh(
            user=user,
            key=key,
            ip=str(right["ip"]),
            command=renderShellCommand(
                createSetupCommands(
                    master_interface=master_interface,
                    vlan_id=vlan_id,
                    vlan_interface=vlan_interface,
                    macvlan_interface=macvlan_interface,
                    address=f"{right_ip}/30",
                    mtu=int(trunk["mtu"]),
                )
            ),
        )
        left_result = runSsh(
            user=user,
            key=key,
            ip=str(left["ip"]),
            command=renderShellCommand(
                [["ping", "-I", macvlan_interface, "-c", str(ping_count), "-W", str(ping_timeout), right_ip]]
            ),
            capture_output=True,
        )
        right_result = runSsh(
            user=user,
            key=key,
            ip=str(right["ip"]),
            command=renderShellCommand(
                [["ping", "-I", macvlan_interface, "-c", str(ping_count), "-W", str(ping_timeout), left_ip]]
            ),
            capture_output=True,
        )
        left_mtu_result = runSsh(
            user=user,
            key=key,
            ip=str(left["ip"]),
            command=renderShellCommand(
                [
                    [
                        "ping",
                        "-I",
                        macvlan_interface,
                        "-M",
                        "do",
                        "-s",
                        str(mtu_payload_bytes),
                        "-c",
                        str(ping_count),
                        "-W",
                        str(ping_timeout),
                        right_ip,
                    ]
                ]
            ),
            capture_output=True,
        )
        right_mtu_result = runSsh(
            user=user,
            key=key,
            ip=str(right["ip"]),
            command=renderShellCommand(
                [
                    [
                        "ping",
                        "-I",
                        macvlan_interface,
                        "-M",
                        "do",
                        "-s",
                        str(mtu_payload_bytes),
                        "-c",
                        str(ping_count),
                        "-W",
                        str(ping_timeout),
                        left_ip,
                    ]
                ]
            ),
            capture_output=True,
        )
        print(
            f"[fabric-validate] PASS trunk={trunk['name']} vlan={vlan_id} "
            f"{left['name']}({left['ip']}) <-> {right['name']}({right['ip']})"
        )
        print(left_result.stdout.strip().splitlines()[-1])
        print(right_result.stdout.strip().splitlines()[-1])
        print(
            f"[fabric-validate] PASS mtu-payload={mtu_payload_bytes} "
            f"trunk={trunk['name']}"
        )
        print(left_mtu_result.stdout.strip().splitlines()[-1])
        print(right_mtu_result.stdout.strip().splitlines()[-1])
    finally:
        for node in (left, right):
            try:
                runSsh(user=user, key=key, ip=str(node["ip"]), command=cleanup)
            except subprocess.CalledProcessError:
                pass


def probeIsolation(
    *,
    user: str,
    key: str,
    left: dict[str, Any],
    right: dict[str, Any],
    trunk: dict[str, Any],
    test_index: int,
    ping_count: int,
    ping_timeout: int,
) -> None:
    """Require equal-IP-subnet macvlans on different VLANs to stay isolated."""
    vlan_end = int(trunk["vlanEnd"])
    vlan_start = int(trunk["vlanStart"])
    if vlan_end <= vlan_start:
        print(f"[fabric-validate] SKIP isolation trunk={trunk['name']}: VLAN range has one ID")
        return

    base = int(ipaddress.ip_address("198.18.0.0")) + (test_index * 4)
    network = ipaddress.ip_network((base, 30))
    left_ip = str(network.network_address + 1)
    right_ip = str(network.network_address + 2)
    vlan_interface = f"pfv{test_index}"
    macvlan_interface = f"pfm{test_index}"
    master_interface = str(trunk["masterInterface"])
    cleanup = createCleanupCommand(vlan_interface, macvlan_interface)

    for node in (left, right):
        runSsh(user=user, key=key, ip=str(node["ip"]), command=cleanup)
    try:
        runSsh(
            user=user,
            key=key,
            ip=str(left["ip"]),
            command=renderShellCommand(
                createSetupCommands(
                    master_interface=master_interface,
                    vlan_id=vlan_end,
                    vlan_interface=vlan_interface,
                    macvlan_interface=macvlan_interface,
                    address=f"{left_ip}/30",
                    mtu=int(trunk["mtu"]),
                )
            ),
        )
        runSsh(
            user=user,
            key=key,
            ip=str(right["ip"]),
            command=renderShellCommand(
                createSetupCommands(
                    master_interface=master_interface,
                    vlan_id=vlan_end - 1,
                    vlan_interface=vlan_interface,
                    macvlan_interface=macvlan_interface,
                    address=f"{right_ip}/30",
                    mtu=int(trunk["mtu"]),
                )
            ),
        )
        ping_result = runSsh(
            user=user,
            key=key,
            ip=str(left["ip"]),
            command=renderShellCommand(
                [["ping", "-I", macvlan_interface, "-c", str(ping_count), "-W", str(ping_timeout), right_ip]]
            ),
            capture_output=True,
            check=False,
        )
        if ping_result.returncode == 0:
            raise RuntimeError(
                f"VLAN isolation failed on trunk={trunk['name']}: "
                f"VLAN {vlan_end} reached VLAN {vlan_end - 1}"
            )
        print(
            f"[fabric-validate] PASS isolation trunk={trunk['name']} "
            f"vlan={vlan_end} !-> vlan={vlan_end - 1}"
        )
    finally:
        for node in (left, right):
            try:
                runSsh(user=user, key=key, ip=str(node["ip"]), command=cleanup)
            except subprocess.CalledProcessError:
                pass


def parseArgs() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--ping-count", type=int, default=3)
    parser.add_argument("--ping-timeout", type=int, default=2)
    parser.add_argument(
        "--mtu-payload-bytes",
        type=int,
        default=None,
        help="Required unfragmented ICMP payload; defaults to fabric.mtu minus 28 bytes.",
    )
    return parser.parse_args()


def main() -> int:
    """Run deterministic cross-hypervisor fabric probes."""
    args = parseArgs()
    data = loadYaml(args.config)
    trunks = fabricVlanTrunks(data)
    if args.mtu_payload_bytes is None:
        args.mtu_payload_bytes = min(int(trunk["mtu"]) for trunk in trunks) - 28 if trunks else 1372
    nodes = selectFirstNodeByHost(data)
    if not trunks:
        print("[fabric-validate] SKIP: no VLAN fabric trunks configured")
        return 0
    if len(nodes) < 2:
        print("[fabric-validate] SKIP: fewer than two hypervisors have VMs")
        return 0
    if args.ping_count < 1 or args.ping_timeout < 1 or args.mtu_payload_bytes < 1:
        raise SystemExit("ping count, timeout, and MTU payload must be positive")

    vm_ssh = data.get("vmSsh") if isinstance(data.get("vmSsh"), dict) else {}
    user = str(vm_ssh.get("user") or "ubuntu")
    key = expandPath(str(vm_ssh.get("key") or "~/.ssh/id_ed25519"))
    left = nodes[0]
    test_index = 0
    for right in nodes[1:]:
        for trunk in trunks:
            probePair(
                user=user,
                key=key,
                left=left,
                right=right,
                trunk=trunk,
                test_index=test_index,
                ping_count=args.ping_count,
                ping_timeout=args.ping_timeout,
                mtu_payload_bytes=args.mtu_payload_bytes,
            )
            test_index += 1
    right = nodes[1]
    for trunk in trunks:
        probeIsolation(
            user=user,
            key=key,
            left=left,
            right=right,
            trunk=trunk,
            test_index=test_index,
            ping_count=args.ping_count,
            ping_timeout=args.ping_timeout,
        )
        test_index += 1
    print(f"[fabric-validate] PASS: {test_index} connectivity/isolation probes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
