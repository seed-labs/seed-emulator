#!/usr/bin/env python3
"""Check a running InternetMap bundle according to B08's test design."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest
from seedemu.testing.compose import docker_compose_command


API = "emulator_api_server.map.seed.emu"
TOPOLOGY = "internetmap_toplogy.map.seed.emu"
GEOGRAPHIC = "internetmap_geo.map.seed.emu"
OBSERVER = "traffic_observer.map.seed.emu"
SERVICES = (API, TOPOLOGY, GEOGRAPHIC, OBSERVER)
LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta."

EXPECTED_ADDRESSES = {
    API: {"172.30.0.10", "10.151.0.16", "10.161.0.16"},
    TOPOLOGY: {"172.30.0.11"},
    GEOGRAPHIC: {"172.30.0.12"},
    OBSERVER: set(),
}
EXPECTED_PORTS = {
    API: {},
    TOPOLOGY: {"80/tcp": "8092"},
    GEOGRAPHIC: {"80/tcp": "8093"},
    OBSERVER: {},  # Observer uses host networking; 8091 is not a Docker port mapping.
}
EXPECTED_HOSTS = {
    "emulator_api_server.map.seed.emu": "10.151.0.16",
    "emulator_api_server-e.map.seed.emu": "172.30.0.10",
    "internetmap_toplogy.map.seed.emu": "172.30.0.11",
    "emulator_api_server-e1.map.seed.emu": "10.161.0.16",
    "internetmap_geo.map.seed.emu": "172.30.0.12",
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
    """Record one check with the corresponding test-design number."""

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


def check_container(test: ComposeRuntimeTest, service: str, info: dict[str, Any]) -> None:
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

    actual_addresses = addresses(info)
    expected_addresses = EXPECTED_ADDRESSES[service]
    network_mode = str(info.get("HostConfig", {}).get("NetworkMode", ""))
    address_ok = actual_addresses == expected_addresses
    if service == OBSERVER:
        address_ok = network_mode == "host"
    record(
        test,
        f"1.2 {service} IP addresses and network mode are correct",
        address_ok,
        f"expected={sorted(expected_addresses)}, actual={sorted(actual_addresses)}, network_mode={network_mode}",
        "docker inspect .NetworkSettings/.HostConfig.NetworkMode",
    )

    bindings = info.get("HostConfig", {}).get("PortBindings") or {}
    actual_ports = {
        container_port: {entry.get("HostPort") for entry in entries or []}
        for container_port, entries in bindings.items()
    }
    expected_ports = EXPECTED_PORTS[service]
    ports_ok = all(host_port in actual_ports.get(container_port, set()) for container_port, host_port in expected_ports.items())
    if not expected_ports:
        ports_ok = not bindings
    record(
        test,
        f"1.5 {service} port mappings are correct",
        ports_ok,
        f"expected={expected_ports}, actual={actual_ports}",
        "docker inspect .HostConfig.PortBindings",
    )


def check_bundle_connectivity(test: ComposeRuntimeTest) -> None:
    # Target 1.3: verify connectivity among the three internetMap_network containers.
    for source, targets in (
        (TOPOLOGY, ("172.30.0.10", "172.30.0.12")),
        (GEOGRAPHIC, ("172.30.0.10", "172.30.0.11")),
    ):
        for target in targets:
            test.exec_check(
                f"1.3 {source} reaches bundle address {target}",
                source,
                f"ping -c 2 -W 2 {target} >/dev/null",
                retries=5,
                interval=2,
                timeout=15,
            )

    # Target 1.4: check AS151/AS161 attached with addInternalNetwork() and
    # remote AS170/AS171 networks reached through emulation routing.
    internal_network_targets = (
        ("10.151.0.254", "directly attached AS151/net0 gateway"),
        ("10.161.0.254", "directly attached AS161/net0 gateway"),
        ("10.170.0.254", "remote AS170/net0 gateway"),
        ("10.171.0.254", "remote AS171/net0 gateway"),
    )
    for gateway, description in internal_network_targets:
        test.exec_check(
            f"1.4 API container reaches the {description} at {gateway}",
            API,
            f"ping -c 2 -W 2 {gateway} >/dev/null",
            retries=5,
            interval=2,
            timeout=15,
        )


def check_etc_hosts(test: ComposeRuntimeTest, service: str) -> None:
    # Target 1.6: verify both file contents and real resolver results.
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
        timeout=30,
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


def http_request(method: str, url: str, body: dict[str, Any] | None = None, timeout: int = 10) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return response.status, None
            text = raw.decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(text)
            except json.JSONDecodeError:
                return response.status, text
    except HTTPError as error:
        raw = error.read()
        try:
            payload: Any = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode("utf-8", errors="replace")
        return error.code, payload
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error)


def check_topology_page(test: ComposeRuntimeTest) -> None:
    # Target 3: verify the page and both topology data APIs over HTTP.
    page_url = "http://127.0.0.1:8092/pro/map"
    page_status, page_body = http_request("GET", page_url)
    record(test, "3.1 Topology Map page responds", page_status == 200 and bool(page_body), f"status={page_status}", f"GET {page_url}")

    for number, resource in (("3.2", "container"), ("3.3", "network")):
        url = f"http://127.0.0.1:8092/api/v1/{resource}"
        status, body = http_request("GET", url)
        valid = status == 200 and isinstance(body, dict) and "result" in body
        detail = f"status={status}" if valid else f"status={status}, body={body}"
        record(test, f"{number} Topology {resource} API responds", valid, detail, f"GET {url}")


def check_traffic_observer(test: ComposeRuntimeTest) -> None:
    # Target 4: verify the 3D page and the proxied filter API over HTTP.
    base = "http://127.0.0.1:8093/traffic-observer"
    filter_expr = "icmp and host 10.161.0.254"
    page_url = "http://127.0.0.1:8093/pro/map/3d"
    page_status, page_body = http_request("GET", page_url)
    record(test, "4.1 Geographic 3D page responds", page_status == 200 and bool(page_body), f"status={page_status}", f"GET {page_url}")

    filter_status, filter_body = http_request("PUT", f"{base}/filter", {"filter": filter_expr})
    filter_ok = filter_status == 200 and isinstance(filter_body, dict) and filter_body.get("filter") == filter_expr
    record(test, "4.2 Traffic Observer sets the capture filter", filter_ok, f"status={filter_status}, body={filter_body}", "PUT /traffic-observer/filter")

    cleanup_status, cleanup_body = http_request("PUT", f"{base}/filter", {"filter": ""})
    cleanup_ok = cleanup_status == 200 and isinstance(cleanup_body, dict) and cleanup_body.get("filter") == ""
    record(test, "4.3 Traffic Observer clears the capture filter", cleanup_ok, f"status={cleanup_status}, body={cleanup_body}", "PUT /traffic-observer/filter (empty)")


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    inspected = {service: inspect_service(test, service) for service in SERVICES}

    for service in SERVICES:
        check_container(test, service, inspected[service])
        check_etc_hosts(test, service)
    check_bundle_connectivity(test)
    check_map_labels(test, inspected[API])
    check_topology_page(test)
    check_traffic_observer(test)

    test.write_summary("b08-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
