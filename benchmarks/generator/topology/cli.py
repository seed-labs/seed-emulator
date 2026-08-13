#!/usr/bin/env python3
"""CLI for declarative topology planning, registration, compilation, and smoke tests."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time
import yaml

from generator.topology.bindings import (
    SUPPORTED_COMPONENTS,
    bind_fault_component,
    load_capability_manifest,
)
from generator.topology.compiler import compile_topology, validate_compiled_output
from generator.topology.models import TopologyRequest
from generator.topology.planner import plan_topology
from generator.topology.registry import (
    BENCHMARKS_DIR,
    list_plans,
    load_plan,
    output_dir,
    register_request,
)


def _run(args, *, cwd=None, timeout=600, check=True):
    completed = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"{(completed.stdout + completed.stderr)[-3000:]}"
        )
    return completed


def smoke_test(
    topology_id: str, *, keep_running: bool = False, build: bool = True
):
    plan = load_plan(topology_id)
    manifest = validate_compiled_output(plan)
    destination = output_dir(topology_id)
    project = f"decl_{topology_id}"
    compose = ["docker", "compose", "--parallel", "4", "-p", project]
    started = datetime.now().isoformat()
    try:
        if build:
            # Compose otherwise schedules every service build at once.  The
            # benchmark builder serializes services while BuildKit still
            # shares content-addressed layers, which is reliable offline and
            # bounded for large generated projects.
            from benchmark_cli import build_compose_services_serially

            build_compose_services_serially(
                destination, timeout_per_service=900, verify_images=True
            )
        # Starting hundreds of namespaces in one Compose transaction can make
        # dockerd unresponsive even when memory admission succeeds. Start
        # dependency helpers first and ramp business assets in small batches.
        asset_services = [item["service"] for item in manifest["assets"]]
        compose_document = yaml.safe_load(
            (destination / "docker-compose.yml").read_text(encoding="utf-8")
        )
        dependency_services = sorted(
            set(compose_document.get("services", {})) - set(asset_services)
        )
        if dependency_services:
            _run(
                [*compose, "up", "-d", "--no-build", *dependency_services],
                cwd=destination, timeout=300,
            )
        start_batch_size = 4
        for offset in range(0, len(asset_services), start_batch_size):
            batch = asset_services[offset:offset + start_batch_size]
            _run(
                [*compose, "up", "-d", "--no-build", "--no-deps", *batch],
                cwd=destination, timeout=300,
            )
            # A cheap bounded daemon health gate prevents a queued start storm.
            _run(["docker", "version"], timeout=60)
        expected = manifest["actual_compose_services"]
        running = 0
        for _attempt in range(60):
            result = _run(
                [
                    "docker", "ps", "--filter",
                    f"label=com.docker.compose.project={project}",
                    "--format", "{{.Names}}",
                ],
                timeout=30,
            )
            running = len([line for line in result.stdout.splitlines() if line])
            # Dependency dummies may exit zero; all declared assets must run.
            if running >= len(manifest["assets"]):
                break
            time.sleep(2)
        else:
            raise RuntimeError(f"only {running}/{len(manifest['assets'])} assets running")
        matrix = test_running_topology(topology_id, convergence_timeout=120)
        report = {
            "topology_id": topology_id,
            "topology_name": plan.topology_name,
            "topology_fingerprint": plan.fingerprint,
            "started_at": started,
            "asset_count": len(manifest["assets"]),
            "compose_service_count": expected,
            "local_gateway_probes": matrix["local_gateway_probes"],
            "ix_peer_probes": matrix["ix_peer_probes"],
            "bgp_sessions": matrix["bgp_sessions"],
            "cross_as_probes": matrix["cross_as_probes"],
            "connectivity_verified": True,
            "kept_running": keep_running,
        }
        report_path = BENCHMARKS_DIR / "reports" / f"TOPOLOGY_{topology_id.upper()}_SMOKE.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report_path, report
    finally:
        if not keep_running:
            _run([*compose, "down", "--remove-orphans"], cwd=destination, timeout=300, check=False)


def _ping(container: str, address: str) -> tuple[bool, str]:
    result = _run(
        ["docker", "exec", container, "ping", "-c", "2", "-W", "2", address],
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    return bool(result.returncode == 0 and re.search(r"(?<!\d)0% packet loss", output)), output


def test_running_topology(topology_id: str, *, convergence_timeout: int = 120):
    """Validate every local/IX edge and a bounded deterministic host matrix."""
    plan = load_plan(topology_id)
    manifest = validate_compiled_output(plan)
    assets = manifest["assets"]
    routers = {item["asn"]: item for item in assets if "Router" in item["role"]}
    hosts = {item["asn"]: item for item in assets if item["role"] == "Host"}
    local_probes = []
    for asn, host in sorted(hosts.items()):
        router = routers[asn]
        gateway = next(
            item["address"].split("/")[0]
            for item in router["interfaces"] if item["name"] == "lan0"
        )
        healthy, output = _ping(host["container"], gateway)
        if not healthy:
            raise RuntimeError(f"AS{asn} local gateway probe failed:\n{output[-1000:]}")
        local_probes.append({"asn": asn, "host": host["container"], "gateway": gateway})
    ix_probes = []
    for link in plan.external_links:
        healthy, output = _ping(routers[link.left_asn]["container"], link.right_address)
        if not healthy:
            raise RuntimeError(f"IX{link.ix_id} peer probe failed:\n{output[-1000:]}")
        ix_probes.append({"ix_id": link.ix_id, "left_asn": link.left_asn, "right_asn": link.right_asn})
    expected_sessions = {asn: 0 for asn in routers}
    for link in plan.external_links:
        expected_sessions[link.left_asn] += 1
        expected_sessions[link.right_asn] += 1
    deadline = time.monotonic() + convergence_timeout
    session_counts = {}
    while time.monotonic() < deadline:
        session_counts = {}
        for asn, router in sorted(routers.items()):
            result = _run(
                ["docker", "exec", router["container"], "birdc", "show", "protocols"],
                timeout=20,
                check=False,
            )
            session_counts[asn] = len(re.findall(r"\bBGP\b.*\bEstablished\b", result.stdout))
        if all(session_counts.get(asn, 0) >= count for asn, count in expected_sessions.items()):
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"eBGP convergence incomplete: {session_counts} != {expected_sessions}")
    pairs = [(left, right) for left in sorted(hosts) for right in sorted(hosts) if left < right]
    if len(pairs) > 64:
        step = max(1, len(pairs) // 64)
        pairs = pairs[::step][:64]
    cross_probes = []
    for left, right in pairs:
        target_ip = next(
            item["address"].split("/")[0]
            for item in hosts[right]["interfaces"] if item["name"] == "lan0"
        )
        healthy, output = _ping(hosts[left]["container"], target_ip)
        if not healthy:
            raise RuntimeError(f"AS{left}->AS{right} host probe failed:\n{output[-1000:]}")
        cross_probes.append({"source_asn": left, "target_asn": right, "target_ip": target_ip})
    return {
        "topology_id": topology_id,
        "topology_fingerprint": plan.fingerprint,
        "local_gateway_probes": local_probes,
        "ix_peer_probes": ix_probes,
        "bgp_sessions": session_counts,
        "cross_as_probes": cross_probes,
    }


def runtime_preflight(topology_id: str):
    """Fail closed before a topology would exhaust the current VM."""
    plan = load_plan(topology_id)
    memory = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0]) // 1024
    total_mb = memory["MemTotal"]
    available_mb = memory["MemAvailable"]
    reserve_mb = max(2048, total_mb // 5)
    cpu_count = os.cpu_count() or 1
    estimate = plan.resource_estimate
    checks = {
        "memory": estimate.memory_mb <= max(0, available_mb - reserve_mb),
        "cpu": estimate.cpu_cores <= cpu_count * 2,
        # Empirical 2026-08-13 gate: this 8-vCPU VM became daemon-unresponsive
        # when 100 business assets were launched simultaneously. Until a
        # throttled 100-node smoke passes, automatic runtime admission must
        # remain below that observed unsafe boundary.
        "container_count": estimate.containers <= 64,
    }
    return {
        "topology_id": topology_id,
        "topology_fingerprint": plan.fingerprint,
        "resource_estimate": estimate.__dict__,
        "host_capacity": {
            "memory_total_mb": total_mb,
            "memory_available_mb": available_mb,
            "memory_reserve_mb": reserve_mb,
            "cpu_count": cpu_count,
            "cpu_overcommit_factor": 2,
            "container_safety_ceiling": 64,
        },
        "checks": checks,
        "runtime_allowed": all(checks.values()),
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Declarative SEED topology generator")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--spec", required=True)
    register = commands.add_parser("register")
    register.add_argument("--spec", required=True)
    register.add_argument("--force", action="store_true")
    compile_parser = commands.add_parser("compile")
    compile_parser.add_argument("--topology-id", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--topology-id", required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--topology-id", required=True)
    smoke.add_argument("--keep-running", action="store_true")
    smoke.add_argument("--no-build", action="store_true")
    bind = commands.add_parser("bind")
    bind.add_argument("--topology-id", required=True)
    bind.add_argument("--component", required=True, choices=SUPPORTED_COMPONENTS)
    bind.add_argument("--sequence", type=int, default=0)
    bind.add_argument("--seed", default="topology-fault-binding")
    test = commands.add_parser("test")
    test.add_argument("--topology-id", required=True)
    test.add_argument("--convergence-timeout", type=int, default=120)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--topology-id", required=True)
    preflight.add_argument("--require-fit", action="store_true")
    commands.add_parser("inventory")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command in {"plan", "register"}:
        request = TopologyRequest.from_json_file(Path(args.spec).resolve())
        result = (
            plan_topology(request)
            if args.command == "plan"
            else register_request(request, force=args.force)
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif args.command == "compile":
        plan = load_plan(args.topology_id)
        destination = compile_topology(plan)
        print(f"compiled_topology={plan.topology_name} output={destination}")
    elif args.command == "validate":
        plan = load_plan(args.topology_id)
        manifest = validate_compiled_output(plan)
        print(
            f"valid_topology={plan.topology_name} assets={len(manifest['assets'])} "
            f"services={manifest['actual_compose_services']}"
        )
    elif args.command == "smoke":
        path, report = smoke_test(
            args.topology_id,
            keep_running=args.keep_running,
            build=not args.no_build,
        )
        print(json.dumps({"report": str(path), **report}, indent=2, sort_keys=True))
    elif args.command == "bind":
        manifest = load_capability_manifest(args.topology_id)
        binding = bind_fault_component(
            manifest, args.component, args.sequence, args.seed
        )
        print(json.dumps(binding, indent=2, sort_keys=True))
    elif args.command == "test":
        print(json.dumps(
            test_running_topology(
                args.topology_id, convergence_timeout=args.convergence_timeout
            ),
            indent=2,
            sort_keys=True,
        ))
    elif args.command == "preflight":
        result = runtime_preflight(args.topology_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.require_fit and not result["runtime_allowed"]:
            return 2
    elif args.command == "inventory":
        print(json.dumps([item.to_dict() for item in list_plans()], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
