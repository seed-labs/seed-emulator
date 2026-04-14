from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parent
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _must_run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    result = _run(cmd, cwd=cwd, env=env, timeout=timeout)
    assert result.returncode == 0, (
        f"command failed: {' '.join(cmd)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def _docker_exec(container: str, shell_cmd: str, *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return _must_run(["docker", "exec", container, "sh", "-lc", shell_cmd], timeout=timeout)


def _docker_exec_maybe(container: str, shell_cmd: str, *, timeout: int = 120) -> str | None:
    result = _run(["docker", "exec", container, "sh", "-lc", shell_cmd], timeout=timeout)
    if result.returncode != 0:
        return None
    return result.stdout


def _wait_http_ok(url: str, *, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = _run(["curl", "-fsS", "-o", "/dev/null", "-w", "%{http_code}", url], timeout=5)
        if result.returncode == 0 and result.stdout.strip() == "200":
            return
        time.sleep(1)
    raise AssertionError(f"HTTP endpoint did not become ready: {url}")


def _wait_until(predicate, *, timeout_s: int = 90, interval_s: int = 2, error_message: str = "condition not met"):
    deadline = time.time() + timeout_s
    last_value = None
    while time.time() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval_s)
    raise AssertionError(f"{error_message}\nlast_value={last_value}")


def _wait_docker_output(
    container: str,
    shell_cmd: str,
    *,
    contains: list[str],
    timeout_s: int = 90,
    interval_s: int = 2,
    error_message: str,
) -> str:
    def _probe():
        text = _docker_exec_maybe(container, shell_cmd)
        if text is None:
            return None
        return text if all(needle in text for needle in contains) else None

    return _wait_until(_probe, timeout_s=timeout_s, interval_s=interval_s, error_message=error_message)


def _wait_command_output(
    cmd: list[str],
    *,
    contains: list[str],
    timeout_s: int = 90,
    interval_s: int = 2,
    error_message: str,
) -> str:
    def _probe():
        result = _run(cmd)
        if result.returncode != 0:
            return None
        return result.stdout if all(needle in result.stdout for needle in contains) else None

    return _wait_until(_probe, timeout_s=timeout_s, interval_s=interval_s, error_message=error_message)


def _assert_runtime_clear() -> None:
    result = _must_run(["docker", "ps", "--format", "{{.Names}}"])
    offenders = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().startswith("as") or line.strip() == "seedemu_internet_map"
    ]
    assert not offenders, f"runtime validation requires a clean emulator environment, found: {offenders}"


def _assert_bridge_nf_disabled() -> None:
    result = _must_run(
        ["sysctl", "net.bridge.bridge-nf-call-iptables", "net.bridge.bridge-nf-call-ip6tables", "net.bridge.bridge-nf-call-arptables"]
    )
    text = result.stdout
    assert " = 0" in text, f"bridge netfilter must be disabled before runtime validation:\n{text}"


def _compose_down(compose_file: Path) -> None:
    _run(["docker", "compose", "-f", str(compose_file), "down", "--remove-orphans"], timeout=300)


def _map_url_from_compose(compose_file: Path) -> str:
    text = compose_file.read_text(encoding="utf-8")
    match = re.search(r"-\s*(?:\$\{SEED_DEMO_MAP_PORT:-)?([0-9]+)(?:\})?:8080/tcp", text)
    host_port = match.group(1) if match else "8080"
    return f"http://127.0.0.1:{host_port}/pro/home"


@pytest.mark.integration
def test_runtime_a12_mixed_backend_fresh_build():
    _assert_runtime_clear()
    _assert_bridge_nf_disabled()

    script = REPO_ROOT / "examples" / "basic" / "A12_bgp_mixed_backend" / "bgp_mixed_backend.py"
    compose = REPO_ROOT / "examples" / "basic" / "A12_bgp_mixed_backend" / "output" / "docker-compose.yml"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["SEED_DEMO_MAP_PORT"] = "18080"

    try:
        _must_run([str(PYTHON), str(script), "amd"], env=env)
        _must_run(["docker", "compose", "-f", str(compose), "build"], timeout=1800)
        _must_run(["docker", "compose", "-f", str(compose), "up", "-d", "--remove-orphans"], timeout=600)

        ospf = _wait_docker_output(
            "as2brd-r2-10.2.0.253",
            'vtysh -c "show ip ospf neighbor"',
            contains=["Full"],
            error_message="A12 OSPF neighbor did not become visible",
        )
        bgp = _wait_docker_output(
            "as2brd-r2-10.2.0.253",
            'vtysh -c "show ip bgp summary"',
            contains=["10.101.0.152", " 1"],
            error_message="A12 BGP summary did not become available",
        )
        host_ping = _wait_command_output(
            ["docker", "exec", "as151h-web-10.151.0.71", "sh", "-lc", "ping -c 2 -W 1 10.152.0.71"],
            contains=["0% packet loss"],
            error_message="A12 host-to-host reachability did not converge",
        )
        router_ping = _wait_command_output(
            ["docker", "exec", "as151brd-router0-10.151.0.254", "sh", "-lc", "ping -c 2 -W 1 10.152.0.254"],
            contains=["0% packet loss"],
            error_message="A12 router-to-router reachability did not converge",
        )
        route = _wait_docker_output(
            "as152brd-router0-10.152.0.254",
            "birdc show route 10.152.0.0/24 all",
            contains=["local_nets", "BGP.large_community: (152, 0, 0)"],
            error_message="A12 local route export did not appear",
        )
        _wait_http_ok(_map_url_from_compose(compose))
    finally:
        _compose_down(compose)


@pytest.mark.integration
def test_runtime_a13_exabgp_fresh_build():
    _assert_runtime_clear()
    _assert_bridge_nf_disabled()

    script = REPO_ROOT / "examples" / "basic" / "A13_exabgp_control_plane" / "exabgp_control_plane.py"
    compose = REPO_ROOT / "examples" / "basic" / "A13_exabgp_control_plane" / "output" / "docker-compose.yml"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["SEED_DEMO_MAP_PORT"] = "18080"
    env["SEED_A13_EXABGP_PORT"] = "5101"

    try:
        _must_run([str(PYTHON), str(script), "amd"], env=env)
        _must_run(["docker", "compose", "-f", str(compose), "build"], timeout=1800)
        _must_run(["docker", "compose", "-f", str(compose), "up", "-d", "--remove-orphans"], timeout=600)

        _wait_http_ok(_map_url_from_compose(compose))
        _wait_http_ok("http://127.0.0.1:5101/")
        procs = _docker_exec(
            "as151h-ExaBGP_Control_Plane_Tool-10.151.0.71",
            'ps -ef | egrep "exabgp|dashboard|event_sink" | grep -v grep',
        ).stdout
        assert "dashboard.py" in procs and "exabgp" in procs and "event_sink.py" in procs
        route = _wait_docker_output(
            "as151brd-router0-10.151.0.254",
            "birdc show route 198.51.100.0/24 all",
            contains=["198.51.100.0/24", "AS65010"],
            error_message="A13 ExaBGP route did not appear on Bird peer",
        )
    finally:
        _compose_down(compose)


@pytest.mark.integration
def test_runtime_a14_observability_fresh_build():
    _assert_runtime_clear()
    _assert_bridge_nf_disabled()

    script = REPO_ROOT / "examples" / "basic" / "A14_bgp_event_looking_glass" / "bgp_event_looking_glass.py"
    compose = REPO_ROOT / "examples" / "basic" / "A14_bgp_event_looking_glass" / "output" / "docker-compose.yml"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["SEED_DEMO_MAP_PORT"] = "18080"
    env["SEED_A14_LG_PORT"] = "5002"
    env["SEED_A14_EVENT_PORT"] = "5003"

    try:
        _must_run([str(PYTHON), str(script), "amd"], env=env)
        _must_run(["docker", "compose", "-f", str(compose), "build"], timeout=1800)
        _must_run(["docker", "compose", "-f", str(compose), "up", "-d", "--remove-orphans"], timeout=600)

        _wait_http_ok(_map_url_from_compose(compose))
        _wait_http_ok("http://127.0.0.1:5002/summary/router0")
        _wait_http_ok("http://127.0.0.1:5003/")
        lg = _docker_exec("as2h-looking-glass-10.2.0.71", 'ps -ef | egrep "frontend|proxy" | grep -v grep').stdout
        assert "frontend" in lg
        exa = _docker_exec("as151h-ExaBGP_Control_Plane_Tool-10.151.0.71", 'ps -ef | egrep "exabgp|dashboard|event_sink" | grep -v grep').stdout
        assert "dashboard.py" in exa and "exabgp" in exa and "event_sink.py" in exa
        lg_ping = _docker_exec("as2h-looking-glass-10.2.0.71", "ping -c 2 -W 1 10.2.0.254").stdout
        assert "0% packet loss" in lg_ping
    finally:
        _compose_down(compose)


@pytest.mark.integration
def test_runtime_exabgp_to_frr_peer():
    _assert_runtime_clear()
    _assert_bridge_nf_disabled()

    out_dir = Path(tempfile.mkdtemp(prefix="frr-exabgp-runtime-", dir="/tmp"))
    compose = out_dir / "docker-compose.yml"

    source = """
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, FrrBgp, Routing
from seedemu.services import ExaBgpService
from seedemu.compiler import Docker, Platform

emu = Emulator()
base = Base()
routing = Routing()
ebgp = Ebgp()
frr = FrrBgp()
exabgp = ExaBgpService()

base.createInternetExchange(100)
as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
as151.createHost('observer').joinNetwork('net0').addPortForwarding(5105, 5000)

frr.enableOn(151, 'router0')
exabgp.install('observer_tool').attachToRouter('router0').setLocalAsn(65010).addAnnouncement('198.51.100.0/24').enableDashboard(5000)
emu.addBinding(Binding('observer_tool', filter=Filter(nodeName='observer', asn=151)))

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(exabgp)
emu.addLayer(frr)
emu.render()
emu.compile(Docker(platform=Platform.AMD64, internetMapEnabled=False), OUTPUT_DIR, override=True)
"""
    script = out_dir / "generate.py"
    script.write_text(source.replace("OUTPUT_DIR", repr(str(out_dir))), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)

    try:
        _must_run([str(PYTHON), str(script)], env=env)
        _must_run(["docker", "compose", "-f", str(compose), "build"], timeout=1800)
        _must_run(["docker", "compose", "-f", str(compose), "up", "-d", "--remove-orphans"], timeout=600)

        _wait_http_ok("http://127.0.0.1:5105/")
        summary = _wait_docker_output(
            "as151brd-router0-10.151.0.254",
            'vtysh -c "show ip bgp summary"',
            contains=["65010", " 1"],
            error_message="FRR peer summary did not converge",
        )
        route = _wait_docker_output(
            "as151brd-router0-10.151.0.254",
            'vtysh -c "show ip bgp 198.51.100.0/24"',
            contains=["198.51.100.0/24", "valid"],
            error_message="FRR peer route did not appear",
        )
    finally:
        _compose_down(compose)
