#!/usr/bin/env python3
"""Source-attributed, baseline-differenced observations for blind benchmarks."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import subprocess
from typing import Callable, Dict, Iterable, List, Optional


Observation = Dict[str, object]
NetworkState = Dict[str, object]

_EMPTY_OR_NOISE = (
    "executable file not found",
    "no such container",
    "is not running",
    "command not found",
)


def _run(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "COMMAND_TIMEOUT"
    except Exception as exc:
        return f"COMMAND_ERROR: {exc}"


def _clean_output(output: str, limit: int = 1600) -> str:
    value = (output or "").strip()
    lowered = value.lower()
    if not value or any(marker in lowered for marker in _EMPTY_OR_NOISE):
        return ""
    return value[:limit]


def _source(
    command: str,
    *,
    container: str = "",
    artifact: str = "",
    interface: str = "",
) -> Dict[str, str]:
    return {
        "command": command,
        "container": container,
        "artifact": artifact,
        "interface": interface,
    }


def _make_observation(
    key: str,
    kind: str,
    command: str,
    output: str,
    *,
    container: str = "",
    artifact: str = "",
    interface: str = "",
) -> Optional[Observation]:
    cleaned = _clean_output(output)
    if not cleaned:
        return None
    return {
        "id": key,
        "kind": kind,
        "source": _source(
            command,
            container=container,
            artifact=artifact,
            interface=interface,
        ),
        "output": cleaned,
    }


def capture_network_state(
    run_command: Callable[[str], str] = _run,
    log: Optional[Callable[[str], None]] = None,
) -> NetworkState:
    """Capture deterministic live evidence without using scenario metadata."""
    if log:
        log("采集带来源的网络健康状态")

    list_command = "docker ps -a --format '{{.Names}}\\t{{.State}}'"
    rows = run_command(list_command).strip().splitlines()
    statuses: Dict[str, str] = {}
    for row in rows:
        name, separator, status = row.partition("\t")
        if name.strip():
            statuses[name.strip()] = status.strip() if separator else "unknown"

    observations: Dict[str, Observation] = {}
    for name in sorted(statuses):
        observation = _make_observation(
            f"container:{name}:state",
            "container_state",
            list_command,
            statuses[name],
            container=name,
            artifact="Docker container state",
        )
        if observation:
            observations[str(observation["id"])] = observation

    running = sorted(
        name for name, status in statuses.items() if status == "running"
    )
    routers = [
        name
        for name in running
        if "router" in name.lower() or "brd" in name.lower() or "core" in name.lower()
    ]
    hosts = [name for name in running if "host" in name.lower()]

    probes: List[Dict[str, str]] = []
    for router in routers:
        probes.extend(
            (
                {
                    "id": f"bird:{router}:protocols",
                    "kind": "routing_protocols",
                    "command": f"docker exec {router} birdc show protocols 2>/dev/null",
                    "container": router,
                    "artifact": "BIRD protocol state",
                },
                {
                    "id": f"bird:{router}:config_summary",
                    "kind": "routing_config",
                    "command": (
                        f"docker exec {router} sh -c \""
                        "grep -E '^[[:space:]]*local .* as [0-9]+;|"
                        "^[[:space:]]*area [0-9]+' /etc/bird/bird.conf "
                        "2>/dev/null | head -n 80\""
                    ),
                    "container": router,
                    "artifact": "BIRD ASN and OSPF area summary",
                },
                {
                    "id": f"ospf:{router}:neighbors",
                    "kind": "ospf_neighbors",
                    "command": (
                        f"docker exec {router} "
                        "birdc show ospf neighbors 2>/dev/null"
                    ),
                    "container": router,
                    "artifact": "BIRD OSPF neighbor state",
                },
                {
                    "id": f"docker:{router}:networks",
                    "kind": "docker_networks",
                    "command": (
                        "docker inspect --format "
                        f"'{{{{json .NetworkSettings.Networks}}}}' {router}"
                    ),
                    "container": router,
                    "artifact": "Docker network attachments",
                },
                {
                    "id": f"link:{router}:all",
                    "kind": "link_state",
                    "command": f"docker exec {router} ip link show",
                    "container": router,
                    "artifact": "kernel link table",
                },
                {
                    "id": f"ipv6:{router}:routes",
                    "kind": "ipv6_routes",
                    "command": f"docker exec {router} ip -6 route show",
                    "container": router,
                    "artifact": "IPv6 route table",
                },
                {
                    "id": f"firewall:{router}:forward",
                    "kind": "firewall",
                    "command": (
                        f"docker exec {router} "
                        "iptables -S FORWARD 2>/dev/null"
                    ),
                    "container": router,
                    "artifact": "iptables FORWARD chain",
                },
                {
                    "id": f"firewall:{router}:output",
                    "kind": "firewall",
                    "command": (
                        f"docker exec {router} "
                        "iptables -S OUTPUT 2>/dev/null"
                    ),
                    "container": router,
                    "artifact": "iptables OUTPUT chain",
                },
            )
        )

    for host in hosts:
        probes.extend(
            (
                {
                    "id": f"docker:{host}:networks",
                    "kind": "docker_networks",
                    "command": (
                        "docker inspect --format "
                        f"'{{{{json .NetworkSettings.Networks}}}}' {host}"
                    ),
                    "container": host,
                    "artifact": "Docker network attachments",
                },
                {
                    "id": f"dns:{host}:resolv",
                    "kind": "dns_config",
                    "command": f"docker exec {host} cat /etc/resolv.conf 2>/dev/null",
                    "container": host,
                    "artifact": "/etc/resolv.conf",
                },
                {
                    "id": f"firewall:{host}:input",
                    "kind": "firewall",
                    "command": f"docker exec {host} iptables -S INPUT 2>/dev/null",
                    "container": host,
                    "artifact": "iptables INPUT chain",
                },
                {
                    "id": f"netem:{host}:qdisc",
                    "kind": "netem",
                    "command": f"docker exec {host} tc -s qdisc show 2>/dev/null",
                    "container": host,
                    "artifact": "root qdisc",
                },
                {
                    "id": f"wireguard:{host}:state",
                    "kind": "wireguard",
                    "command": f"docker exec {host} wg show 2>/dev/null",
                    "container": host,
                    "artifact": "WireGuard state",
                },
            )
        )

    # Topology-wide control-plane sensors are generic. Do not add probes for
    # scenario-named /tmp/benchmark_* artifacts here: doing so turns the blind
    # baseline delta into an answer oracle. Config-lint scenarios must discover
    # their input with attributed read-only commands and are reported in a
    # separate track.
    probes.extend(
        (
            {
                "id": "routing:route_reflector:running_config",
                "kind": "route_reflector",
                "command": (
                    "docker exec as9brd-edge0-10.114.0.9 "
                    "vtysh -c 'show running-config' 2>/dev/null"
                ),
                "container": "as9brd-edge0-10.114.0.9",
                "artifact": "FRR running-config",
            },
            {
                "id": "routing:mpls:ldp",
                "kind": "mpls_ldp",
                "command": (
                    "docker exec as2r-core_100_101-10.2.0.253 "
                    "vtysh -c 'show mpls ldp neighbor' 2>/dev/null"
                ),
                "container": "as2r-core_100_101-10.2.0.253",
                "artifact": "FRR MPLS LDP state",
            },
        )
    )

    capture_profile = "full"
    if len(statuses) >= 100:
        # Large generated Internets currently exercise router/control-plane
        # faults. Preserve every container state and every router's BIRD,
        # compact configuration, Docker attachment, and firewall evidence, but
        # avoid hundreds of unrelated host DNS/tc/wg subprocesses. Selection
        # depends only on topology size and roles, not scenario metadata, so
        # blind evaluation remains blind.
        capture_profile = "large_router_control_plane"
        router_set = set(routers)
        probes = [
            probe
            for probe in probes
            if probe.get("container") in router_set
            and probe.get("kind") in {
                "routing_protocols",
                "routing_config",
                "docker_networks",
                "firewall",
            }
        ]

    def execute(probe: Dict[str, str]) -> Optional[Observation]:
        try:
            output = run_command(probe["command"], timeout=8)
        except TypeError:
            output = run_command(probe["command"])
        return _make_observation(
            probe["id"],
            probe["kind"],
            probe["command"],
            output,
            container=probe.get("container", ""),
            artifact=probe.get("artifact", ""),
            interface=probe.get("interface", ""),
        )

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(probes)))) as pool:
        for observation in pool.map(execute, probes):
            if observation:
                observations[str(observation["id"])] = observation

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "capture_profile": capture_profile,
        "probe_count": len(probes),
        "observations": observations,
    }


def diff_network_states(
    baseline: NetworkState,
    current: NetworkState,
) -> List[Dict[str, object]]:
    """Return only changed observations, preserving source attribution."""
    before = baseline.get("observations", {}) or {}
    after = current.get("observations", {}) or {}
    changes: List[Dict[str, object]] = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        old_output = old.get("output", "") if old else ""
        new_output = new.get("output", "") if new else ""
        if old_output == new_output:
            continue
        source = (new or old or {}).get("source", {})
        changes.append(
            {
                "id": key,
                "kind": (new or old or {}).get("kind", "unknown"),
                "change": (
                    "added" if old is None else "removed" if new is None else "changed"
                ),
                "source": source,
                "baseline": old_output,
                "current": new_output,
            }
        )
    return changes


def format_state_delta(
    baseline: NetworkState,
    current: NetworkState,
    *,
    max_changes: int = 80,
) -> str:
    """Format a compact blind prompt containing only baseline deltas."""
    changes = diff_network_states(baseline, current)
    lines = [
        "## 健康基线与故障后状态差异",
        "",
        "以下内容只包含实时采集后发生变化的观测；每条观测都包含来源。",
        "来源是诊断证据，不是场景元数据或标准修复答案。",
        "",
    ]
    if not changes:
        lines.extend(
            (
                "未发现稳定的自动观测差异。请使用带来源的只读命令继续定位，",
                "不要把未变化的背景状态当作故障证据。",
            )
        )
        return "\n".join(lines)

    for change in changes[:max_changes]:
        source = change.get("source", {}) or {}
        lines.extend(
            (
                f"### {change['change'].upper()}: {change['id']}",
                f"- kind: {change['kind']}",
                f"- command: `{source.get('command', '')}`",
                f"- container: `{source.get('container', '')}`",
                f"- artifact: `{source.get('artifact', '')}`",
                f"- interface: `{source.get('interface', '')}`",
                "- baseline:",
                "```",
                str(change.get("baseline", ""))[:900],
                "```",
                "- current:",
                "```",
                str(change.get("current", ""))[:900],
                "```",
                "",
            )
        )
    if len(changes) > max_changes:
        lines.append(f"另有 {len(changes) - max_changes} 条变化被截断。")
    return "\n".join(lines)
