#!/usr/bin/env python3
"""CLI for declarative topology planning, registration, compilation, and smoke tests."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import time

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


def smoke_test(topology_id: str, *, keep_running: bool = False):
    plan = load_plan(topology_id)
    manifest = validate_compiled_output(plan)
    destination = output_dir(topology_id)
    project = f"decl_{topology_id}"
    compose = ["docker", "compose", "-p", project]
    started = datetime.now().isoformat()
    try:
        _run([*compose, "up", "-d", "--build"], cwd=destination, timeout=1800)
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
        hosts = manifest["fault_component_bindings"]["container_stopped"]
        if len(hosts) < 2:
            raise RuntimeError("smoke test requires at least two hosts")
        target_asset = next(item for item in manifest["assets"] if item["container"] == hosts[-1])
        target_ip = next(
            iface["address"].split("/")[0]
            for iface in target_asset["interfaces"]
            if iface["name"] == "lan0"
        )
        output = ""
        convergence_deadline = time.monotonic() + 120
        while time.monotonic() < convergence_deadline:
            probe = _run(
                ["docker", "exec", hosts[0], "ping", "-c", "3", "-W", "2", target_ip],
                timeout=30,
                check=False,
            )
            output = probe.stdout + probe.stderr
            if probe.returncode == 0 and re.search(r"(?<!\d)0% packet loss", output):
                break
            time.sleep(min(5, max(0, convergence_deadline - time.monotonic())))
        else:
            raise RuntimeError(
                "end-to-end ping did not converge within 120 seconds:\n"
                f"{output[-2000:]}"
            )
        report = {
            "topology_id": topology_id,
            "topology_name": plan.topology_name,
            "topology_fingerprint": plan.fingerprint,
            "started_at": started,
            "asset_count": len(manifest["assets"]),
            "compose_service_count": expected,
            "source_container": hosts[0],
            "target_container": hosts[-1],
            "target_ip": target_ip,
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
    bind = commands.add_parser("bind")
    bind.add_argument("--topology-id", required=True)
    bind.add_argument("--component", required=True, choices=SUPPORTED_COMPONENTS)
    bind.add_argument("--sequence", type=int, default=0)
    bind.add_argument("--seed", default="topology-fault-binding")
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
        path, report = smoke_test(args.topology_id, keep_running=args.keep_running)
        print(json.dumps({"report": str(path), **report}, indent=2, sort_keys=True))
    elif args.command == "bind":
        manifest = load_capability_manifest(args.topology_id)
        binding = bind_fault_component(
            manifest, args.component, args.sequence, args.seed
        )
        print(json.dumps(binding, indent=2, sort_keys=True))
    elif args.command == "inventory":
        print(json.dumps([item.to_dict() for item in list_plans()], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
