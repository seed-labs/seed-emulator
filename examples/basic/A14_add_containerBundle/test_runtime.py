#!/usr/bin/env python3
"""Check a running ContainerBundle according to A14's test design."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest
from seedemu.testing.compose import docker_compose_command


APP = "demo-app.demo.seed"
HELPER = "demo-helper.demo.seed"
LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta."

EXPECTED_ADDRESSES = {
    APP: {"172.31.0.10", "10.151.0.16", "10.152.0.16"},
    HELPER: {"172.31.0.11"},
}
EXPECTED_PORTS = {APP: {"8080/tcp": "8090"}, HELPER: {}}
EXPECTED_HOSTS = {
    "demo-app-e.demo.seed": "172.31.0.10",
    "demo-helper-e.demo.seed": "172.31.0.11",
    "demo-app-demo_bundle_network": "172.31.0.10",
    "demo-helper-demo_bundle_network": "172.31.0.11",
    "demo-app.demo.seed": "10.151.0.16",
    "demo-app-net_151_net0": "10.151.0.16",
    "demo-app-net_152_net0": "10.152.0.16",
}
REQUIRED_MAP_LABELS = (
    "asn",
    "nodename",
    "role",
    "net.0.name",
    "net.0.address",
    "custom",
)


def record(test: ComposeRuntimeTest, name: str, passed: bool, detail: str, command: str) -> None:
    """Record one check; failures are included in the final terminal summary."""

    test.results.append(
        {
            "name": name,
            "service": "<runtime>",
            "command": command,
            "exit": 0 if passed else 1,
            "stdout": detail if passed else "",
            "stderr": "" if passed else detail,
            "status": "passed" if passed else "failed",
        }
    )


def run(command: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def inspect_service(test: ComposeRuntimeTest, service: str) -> dict[str, Any]:
    """Inspect a real container in the running Compose project."""

    compose = docker_compose_command()
    cwd = test.compose_file.parent
    ps = run(compose + ["-f", str(test.compose_file), "ps", "-q", service], cwd)
    container_id = ps.stdout.strip()
    if ps.returncode != 0 or not container_id:
        record(test, f"1.1 {service} container exists", False, ps.stderr or "container ID was not found", "docker compose ps -q")
        return {}

    docker = shutil.which("docker") or "docker"
    result = run([docker, "inspect", container_id], cwd)
    try:
        payload = json.loads(result.stdout) if result.returncode == 0 else []
        info = payload[0] if payload else {}
    except (json.JSONDecodeError, IndexError, TypeError):
        info = {}
    record(test, f"1.1 {service} can be inspected", bool(info), result.stderr or container_id, "docker inspect")
    return info


def addresses(info: dict[str, Any]) -> set[str]:
    return {
        str(item.get("IPAddress", ""))
        for item in info.get("NetworkSettings", {}).get("Networks", {}).values()
        if item.get("IPAddress")
    }


def check_container_state_and_addresses(
    test: ComposeRuntimeTest, service: str, info: dict[str, Any]
) -> None:
    if not info:
        return
    state = info.get("State", {})
    restart_count = int(info.get("RestartCount", 0) or 0)
    record(
        test,
        f"1.1 {service} is running normally",
        state.get("Running") is True and restart_count == 0,
        f"state={state.get('Status')}, restart_count={restart_count}",
        "docker inspect .State/.RestartCount",
    )
    actual = addresses(info)
    expected = EXPECTED_ADDRESSES[service]
    record(
        test,
        f"1.2 {service} IP addresses match the assigned values",
        actual == expected,
        f"expected={sorted(expected)}, actual={sorted(actual)}",
        "docker inspect .NetworkSettings.Networks",
    )


def check_connectivity(test: ComposeRuntimeTest) -> None:
    # Target 1.3: verify bidirectional connectivity between bundle containers.
    test.exec_check("1.3 app reaches helper", APP, "ping -c 2 -W 2 172.31.0.11 >/dev/null", retries=5, interval=2, timeout=15)
    test.exec_check("1.3 helper reaches app", HELPER, "ping -c 2 -W 2 172.31.0.10 >/dev/null", retries=5, interval=2, timeout=15)

    # Target 1.4: check AS151/AS152 attached with addInternalNetwork() and
    # remote AS170/AS171 networks reached through emulation routing.
    internal_network_targets = (
        ("10.151.0.254", "directly attached AS151/net0 gateway"),
        ("10.152.0.254", "directly attached AS152/net0 gateway"),
        ("10.170.0.254", "remote AS170/net0 gateway"),
        ("10.171.0.254", "remote AS171/net0 gateway"),
    )
    for gateway, description in internal_network_targets:
        test.exec_check(
            f"1.4 app reaches the {description} at {gateway}",
            APP,
            f"ping -c 2 -W 2 {gateway} >/dev/null",
            retries=5,
            interval=2,
            timeout=15,
        )


def check_ports(test: ComposeRuntimeTest, service: str, info: dict[str, Any]) -> None:
    if not info:
        return
    bindings = info.get("HostConfig", {}).get("PortBindings") or {}
    actual = {
        container_port: {entry.get("HostPort") for entry in entries or []}
        for container_port, entries in bindings.items()
    }
    expected = EXPECTED_PORTS[service]
    passed = all(host_port in actual.get(container_port, set()) for container_port, host_port in expected.items())
    if not expected:
        passed = not bindings
    record(
        test,
        f"1.5 {service} port mappings are correct",
        passed,
        f"expected={expected}, actual={actual}",
        "docker inspect .HostConfig.PortBindings",
    )


def check_etc_hosts(test: ComposeRuntimeTest, service: str) -> None:
    # Target 1.6: verify both /etc/hosts contents and resolver results.
    commands: list[str] = []
    for name, ip_address in EXPECTED_HOSTS.items():
        escaped_name = name.replace(".", "\\.")
        escaped_ip = ip_address.replace(".", "\\.")
        commands.append(f"grep -Eq '^{escaped_ip}[[:space:]]+{escaped_name}([[:space:]]|$)' /etc/hosts")
        commands.append(
            f"getent ahostsv4 {name} | awk '$1 == \"{ip_address}\" {{found=1}} END {{exit !found}}'"
        )
    test.exec_check(
        f"1.6 {service} contains and resolves the added hosts records",
        service,
        " && ".join(commands),
        retries=5,
        interval=2,
        timeout=25,
    )


def check_map_labels(test: ComposeRuntimeTest, info: dict[str, Any]) -> None:
    if not info:
        return
    labels = info.get("Config", {}).get("Labels", {}) or {}
    missing = [f"{LABEL_PREFIX}{key}" for key in REQUIRED_MAP_LABELS if f"{LABEL_PREFIX}{key}" not in labels]
    custom_value = labels.get(f"{LABEL_PREFIX}custom")
    record(
        test,
        "2.1 show_on_map labels are complete and custom has the correct value",
        not missing and custom_value == "custom",
        f"missing={missing}, custom={custom_value!r}",
        "docker inspect .Config.Labels",
    )


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    app_info = inspect_service(test, APP)
    helper_info = inspect_service(test, HELPER)

    for service, info in ((APP, app_info), (HELPER, helper_info)):
        check_container_state_and_addresses(test, service, info)
        check_ports(test, service, info)
        check_etc_hosts(test, service)
    check_connectivity(test)
    check_map_labels(test, app_info)

    test.write_summary("a14-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
