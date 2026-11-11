#!/usr/bin/env python3
"""Check a running InternetMap bundle according to B08's test design."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
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

# Avoid running the browser download more than once in the same test process.
_PLAYWRIGHT_INSTALL_ATTEMPTED = False
_PLAYWRIGHT_INSTALL_ERROR = ""


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


def http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: int = 10) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")) if raw else None
    except HTTPError as error:
        raw = error.read()
        try:
            payload: Any = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode("utf-8", errors="replace")
        return error.code, payload
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error)


def launch_chromium(playwright: Any) -> Any:
    """Launch Chromium, installing Playwright's managed browser when missing."""

    global _PLAYWRIGHT_INSTALL_ATTEMPTED, _PLAYWRIGHT_INSTALL_ERROR

    def concise(error: Exception) -> str:
        return str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__

    launch_errors: list[str] = []
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as error:
        initial_error = str(error)
        launch_errors.append(f"Playwright Chromium: {concise(error)}")

    # The Python package is already available at this point. If only its
    # version-matched browser is absent, download it with the exact interpreter
    # that is running this test, then retry the normal Playwright launch.
    if "Executable doesn't exist" in initial_error and not _PLAYWRIGHT_INSTALL_ATTEMPTED:
        _PLAYWRIGHT_INSTALL_ATTEMPTED = True
        try:
            install = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                cwd=str(Path(__file__).resolve().parent),
                text=True,
                capture_output=True,
                timeout=1200,
                check=False,
            )
            if install.returncode == 0:
                try:
                    return playwright.chromium.launch(headless=True)
                except Exception as error:
                    _PLAYWRIGHT_INSTALL_ERROR = (
                        "Chromium was downloaded but could not be launched: "
                        f"{concise(error)}"
                    )
            else:
                output = (install.stderr or install.stdout).strip()
                last_line = output.splitlines()[-1] if output else "unknown installation error"
                _PLAYWRIGHT_INSTALL_ERROR = (
                    f"automatic Chromium installation exited with {install.returncode}: {last_line}"
                )
        except subprocess.TimeoutExpired:
            _PLAYWRIGHT_INSTALL_ERROR = "automatic Chromium installation timed out after 1200 seconds"
        except OSError as error:
            _PLAYWRIGHT_INSTALL_ERROR = f"automatic Chromium installation could not start: {concise(error)}"

    if _PLAYWRIGHT_INSTALL_ERROR:
        launch_errors.append(_PLAYWRIGHT_INSTALL_ERROR)

    configured = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "").strip()
    candidates = [
        configured,
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        shutil.which("google-chrome") or "",
        shutil.which("google-chrome-stable") or "",
        shutil.which("chrome") or "",
    ]
    attempted: set[str] = set()
    for executable in candidates:
        if not executable or executable in attempted:
            continue
        attempted.add(executable)
        try:
            return playwright.chromium.launch(headless=True, executable_path=executable)
        except Exception as error:
            launch_errors.append(f"{executable}: {concise(error)}")

    detail = launch_errors[-1] if launch_errors else "no Chromium executable was found"
    raise RuntimeError(
        "Chromium is unavailable after automatic installation and system-browser fallback. "
        "Run `python -m playwright install chromium` manually or set "
        f"PLAYWRIGHT_CHROMIUM_EXECUTABLE. Last error: {detail}"
    )


def check_topology_page(test: ComposeRuntimeTest) -> None:
    # Target 3: use a real browser to verify that the vis canvas is rendered;
    # an HTTP 200 response alone is insufficient.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        record(test, "3.1 Topology Map loads the topology", False, f"Playwright is unavailable: {error}", "Playwright Chromium")
        return

    try:
        with sync_playwright() as playwright:
            browser = launch_chromium(playwright)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto("http://127.0.0.1:8092/pro/map", wait_until="networkidle", timeout=60_000)
            canvas = page.locator('[data-testid="base-map-canvas"] canvas').first
            canvas.wait_for(state="visible", timeout=30_000)
            size = canvas.evaluate("el => ({width: el.width, height: el.height})")
            status, containers = http_json("GET", "http://127.0.0.1:8092/api/v1/container")
            _, networks = http_json("GET", "http://127.0.0.1:8092/api/v1/network")
            rendered = size["width"] > 0 and size["height"] > 0
            data_loaded = (
                status == 200
                and isinstance(containers, dict)
                and bool(containers.get("result"))
                and isinstance(networks, dict)
                and bool(networks.get("result"))
            )
            browser.close()
        record(
            test,
            "3.1 Topology Map loads the topology",
            rendered and data_loaded,
            f"canvas={size}, containers_loaded={bool(containers.get('result')) if isinstance(containers, dict) else False}, "
            f"networks_loaded={bool(networks.get('result')) if isinstance(networks, dict) else False}",
            "Playwright Chromium /pro/map",
        )
    except Exception as error:  # Record all Playwright-specific exception types uniformly.
        record(test, "3.1 Topology Map loads the topology", False, str(error), "Playwright Chromium /pro/map")


def check_traffic_observer(test: ComposeRuntimeTest) -> None:
    # Target 4: prepare live capture, open the 3D page so that it creates the
    # packet WebSocket, generate traffic, and verify real eBPF data on it.
    base = "http://127.0.0.1:8093/traffic-observer"
    filter_expr = "icmp and host 10.161.0.254"
    browser = None
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            record(test, "4.3 3D page creates the Traffic Observer WebSocket", False, f"Playwright is unavailable: {error}", "Playwright Chromium")
            return

        interface_status, interfaces = http_json("PUT", f"{base}/interfaces")
        interfaces_ok = (
            interface_status == 200
            and isinstance(interfaces, dict)
            and int(interfaces.get("discoveredContainerInterfaces", 0)) > 0
        )
        record(test, "4.1 Traffic Observer discovers container interfaces", interfaces_ok, f"status={interface_status}, body={interfaces}", "PUT /interfaces")
        if not interfaces_ok:
            return

        # EmulatorTopologyPage loads the current filter during mounting and
        # connects its WebSocket only when that filter is non-empty.
        filter_status, filter_body = http_json("PUT", f"{base}/filter", {"filter": filter_expr})
        filter_ok = filter_status == 200 and isinstance(filter_body, dict) and filter_body.get("filter") == filter_expr
        record(test, "4.2 Traffic Observer enables the requested capture filter", filter_ok, f"status={filter_status}, body={filter_body}", "PUT /filter")
        if not filter_ok:
            return

        playwright_context = sync_playwright().start()
        browser = launch_chromium(playwright_context)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        observed_websockets: list[str] = []
        packet_websockets: list[str] = []
        packet_events: list[dict[str, Any]] = []

        def on_websocket(websocket: Any) -> None:
            observed_websockets.append(websocket.url)
            if "/traffic-observer/ws/packets" not in websocket.url:
                return
            packet_websockets.append(websocket.url)

            def on_frame(payload: str | bytes) -> None:
                try:
                    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
                    event = json.loads(text)
                    if isinstance(event, dict):
                        packet_events.append(event)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return

            websocket.on("framereceived", on_frame)

        page.on("websocket", on_websocket)
        page.goto("http://127.0.0.1:8093/pro/map/3d", wait_until="domcontentloaded", timeout=60_000)
        deadline = time.monotonic() + 20
        while not packet_websockets and time.monotonic() < deadline:
            page.wait_for_timeout(250)
        websocket_ok = bool(packet_websockets)
        record(
            test,
            "4.3 3D page creates the Traffic Observer WebSocket",
            websocket_ok,
            f"packet_websockets={packet_websockets}, all_websockets={observed_websockets}",
            "Playwright /pro/map/3d",
        )
        if not websocket_ok:
            return

        ping = test.exec(API, "ping -c 4 -W 2 10.161.0.254 >/dev/null", timeout=15)
        record(test, "4.4 API container generates matching traffic", ping["exit"] == 0, str(ping), "ping 10.161.0.254")
        if ping["exit"] != 0:
            return

        deadline = time.monotonic() + 20
        matched: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            page.wait_for_timeout(250)
            for event in packet_events:
                if event.get("type") != "packet":
                    continue
                endpoints = {str(event.get("sourceIp", "")), str(event.get("destIp", ""))}
                if event.get("ipProtocol") == "icmp" and "10.161.0.254" in endpoints:
                    matched = event
                    break
            if matched is not None:
                break
        record(
            test,
            "4.5 3D page receives matching captured packet data",
            matched is not None,
            f"matched={matched}" if matched else "no matching ICMP packet arrived within 20 seconds",
            "Playwright WebSocket /traffic-observer/ws/packets",
        )
    except Exception as error:
        record(test, "4.5 Traffic Observer real capture workflow", False, str(error), "Playwright/Traffic Observer API")
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if "playwright_context" in locals():
            try:
                playwright_context.stop()
            except Exception:
                pass
        cleanup_status, cleanup_body = http_json("PUT", f"{base}/filter", {"filter": ""})
        record(
            test,
            "4.6 Traffic Observer clears the capture filter",
            cleanup_status == 200 and isinstance(cleanup_body, dict) and cleanup_body.get("filter") == "",
            f"status={cleanup_status}, body={cleanup_body}",
            "PUT /filter (empty)",
        )


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
