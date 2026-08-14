#!/usr/bin/env python3
"""Run or inspect the production generator for a group-meeting demo.

The default ``plan`` mode is safe and fast: it does not launch containers.
``real`` starts only the compiled application-pilot Compose project and always
stops it in a finally block. ``evidence`` verifies the committed real run
without changing Docker state.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, Mapping


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BENCHMARKS_DIR / "reports"
PLAN_REQUEST = (
    BENCHMARKS_DIR
    / "generator/bundle/examples/production_application_request.json"
)
REAL_REQUEST = (
    BENCHMARKS_DIR
    / "generator/bundle/examples/production_application_e2e_request.json"
)
COMMITTED_EVIDENCE = REPORTS_DIR / "PRODUCTION_APPLICATION_E2E_V2"
COMPOSE_FILE = (
    BENCHMARKS_DIR
    / "generated/declarative/multi_agent_application_pilot/output/docker-compose.yml"
)
SNAP_DOCKER_WRAPPER = Path("/snap/bin/docker")
SNAP_DOCKER_BINARY = Path("/snap/docker/current/bin/docker")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def display_command(command: Iterable[object]) -> str:
    return " ".join(shlex.quote(str(item)) for item in command)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {display_command(command)}", flush=True)
    return subprocess.run(
        command,
        cwd=BENCHMARKS_DIR,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )


def default_workspace(mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPORTS_DIR / "group_meeting_demo" / stamp / f"{mode}_run"


def safe_workspace(value: Path) -> Path:
    workspace = value.resolve()
    reports = REPORTS_DIR.resolve()
    require(
        workspace != reports and reports in workspace.parents,
        "demo workspace must be a child of benchmarks/reports",
    )
    require(not workspace.exists(), f"refusing to reuse existing workspace: {workspace}")
    return workspace


def selected_faults(workspace: Path, request_id: str) -> list[Dict[str, Any]]:
    artifact = read_json(workspace / "artifacts" / f"{request_id}_faults.json")
    result = []
    for fault in artifact["payload"]["faults"]:
        result.append(
            {
                "fault_id": fault["fault_id"],
                "fault_type": fault["fault_type"],
                "container": fault["selector"]["container"],
                "must_break": fault["expectations"]["must_break"],
                "must_preserve": fault["expectations"]["must_preserve"],
            }
        )
    return result


def verify_common(workspace: Path, elapsed_seconds: float | None) -> Dict[str, Any]:
    summary = read_json(workspace / "summary.json")
    coordinator = read_json(workspace / "coordinator.json")
    quality = read_json(workspace / "quality.json")
    scale = read_json(workspace / "scale_validation.json")
    tasks: Mapping[str, Mapping[str, Any]] = coordinator["tasks"]
    roles = sorted(task["definition"]["agent_role"] for task in tasks.values())

    require(coordinator["result"] == "complete", "Agent DAG is incomplete")
    require(len(tasks) == 9, "the production DAG must contain nine workers")
    require(all(task["status"] == "complete" for task in tasks.values()), "a worker failed")
    require(summary["worker_count"] == 9, "summary worker count is invalid")
    require(summary["quality_passed"] and quality["passed"], "quality gate failed")
    require(all(quality["checks"].values()), "one or more quality checks failed")
    require(summary["scale_passed"] and scale["passed"], "scale validation failed")
    require(all(item["passed"] for item in scale["results"]), "a scale case failed")

    return {
        "workspace": str(workspace),
        "elapsed_seconds": elapsed_seconds,
        "generator": {
            "request_id": summary["request_id"],
            "coordinator_result": summary["coordinator_result"],
            "worker_count": summary["worker_count"],
            "quality_passed": summary["quality_passed"],
            "scale_passed": summary["scale_passed"],
            "qualification_status": summary["qualification_status"],
            "bundle_fingerprint": summary["bundle_fingerprint"],
            "generator_contract_sha256": summary["generator_contract_sha256"],
        },
        "workers": {"count": len(tasks), "roles": roles, "all_complete": True},
        "faults": selected_faults(workspace, summary["request_id"]),
        "quality": {
            "passed": quality["passed"],
            "difficulty": quality["difficulty"],
            "difficulty_score": quality["difficulty_score"],
            "checks": quality["checks"],
            "scenario_signature": quality["scenario_signature"],
        },
        "scales": [
            {
                "asset_count": item["asset_count"],
                "mode": item["execution_mode"],
                "passed": item["passed"],
            }
            for item in scale["results"]
        ],
    }


def verify_real(workspace: Path, result: Dict[str, Any]) -> None:
    summary = read_json(workspace / "summary.json")
    qualification = read_json(workspace / "qualification.json")
    require(qualification["status"] == "qualified", "formal qualification failed")
    require(len(qualification["receipts"]) >= 2, "qualification needs two receipts")
    require(summary["qualification_status"] == "qualified", "summary is not qualified")
    require(summary["release"], "real demo did not publish a release")

    phases = set()
    receipt_results = []
    for receipt_ref in qualification["receipts"]:
        receipt_path = Path(receipt_ref["path"])
        require(receipt_path.is_file(), f"missing receipt: {receipt_path}")
        require(digest(receipt_path) == receipt_ref["sha256"], "receipt hash mismatch")
        receipt = read_json(receipt_path)
        require(receipt["passed"], "lifecycle receipt failed")
        require(receipt["blind_mode"] and not receipt["ai_invoked"], "not a no-AI blind run")
        require(not receipt["topology_tainted"], "topology was left tainted")
        require(not receipt["cleanup_failures"], "lifecycle cleanup failed")
        require(all(test["passed"] for test in receipt["tests"]), "a lifecycle test failed")
        phases.update(test["phase"] for test in receipt["tests"])
        receipt_results.append(
            {
                "run_id": receipt["run_id"],
                "passed": receipt["passed"],
                "blind_mode": receipt["blind_mode"],
                "ai_invoked": receipt["ai_invoked"],
                "topology_tainted": receipt["topology_tainted"],
            }
        )
    require(phases == {"baseline", "active", "recovery"}, "lifecycle phases are incomplete")

    release = summary["release"]
    public_path = Path(release["public_path"])
    private_path = Path(release["private_path"])
    require(digest(public_path) == release["public_sha256"], "public release hash mismatch")
    require(digest(private_path) == release["private_sha256"], "private release hash mismatch")
    require(public_path.resolve() != private_path.resolve(), "public/private paths overlap")
    public_mode = stat.S_IMODE(public_path.stat().st_mode)
    private_mode = stat.S_IMODE(private_path.stat().st_mode)
    require(private_mode == 0o600, "private bundle mode must be 0600")

    result["lifecycle"] = {
        "status": qualification["status"],
        "qualification_level": qualification["qualification_level"],
        "receipt_count": len(receipt_results),
        "phases": sorted(phases),
        "receipts": receipt_results,
        "qualification_sha256": qualification["qualification_sha256"],
    }
    result["release"] = {
        "version": release["version"],
        "public_path": str(public_path),
        "private_path": str(private_path),
        "public_mode": oct(public_mode),
        "private_mode": oct(private_mode),
        "public_sha256": release["public_sha256"],
        "private_sha256": release["private_sha256"],
        "release_fingerprint": release["release_fingerprint"],
    }


def generate(mode: str, request: Path, workspace: Path, release_version: str) -> Dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "generator.bundle.cli",
        "generate",
        "--request",
        str(request),
        "--workspace",
        str(workspace),
        "--release-version",
        release_version,
    ]
    started = time.monotonic()
    completed = run(command, capture=True)
    elapsed = round(time.monotonic() - started, 2)
    print(completed.stdout, end="")
    result = verify_common(workspace, elapsed)
    if mode == "real":
        verify_real(workspace, result)
    return result


def run_real(request: Path, workspace: Path, release_version: str) -> Dict[str, Any]:
    require(COMPOSE_FILE.is_file(), f"compiled Compose file is missing: {COMPOSE_FILE}")
    compose_cli = str(SNAP_DOCKER_WRAPPER) if SNAP_DOCKER_WRAPPER.is_file() else "docker"
    run([compose_cli, "version", "--format", "{{.Server.Version}}"], capture=True)
    compose = [compose_cli, "compose", "-f", str(COMPOSE_FILE)]
    run(compose + ["up", "-d"])
    original_path = os.environ.get("PATH", "")
    if SNAP_DOCKER_BINARY.is_file() and os.access(SNAP_DOCKER_BINARY, os.X_OK):
        # The Snap launcher can intermittently fail with exit 46 while creating
        # a transient systemd scope. Lifecycle probes need only the Docker CLI,
        # so use the packaged binary directly; Compose still uses the launcher.
        os.environ["PATH"] = f"{SNAP_DOCKER_BINARY.parent}:{original_path}"
        print(f"lifecycle_docker={SNAP_DOCKER_BINARY}", flush=True)
    try:
        return generate("real", request, workspace, release_version)
    finally:
        os.environ["PATH"] = original_path
        print("demo_cleanup=compose_down", flush=True)
        subprocess.run(
            compose + ["down", "--remove-orphans"],
            cwd=BENCHMARKS_DIR,
            check=False,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("plan", "real", "evidence"),
        default="plan",
        help="plan: fast/no Docker; real: two Docker runs; evidence: inspect committed E2E",
    )
    parser.add_argument("--request", type=Path, help="override the mode's request JSON")
    parser.add_argument("--workspace", type=Path, help="new output directory under reports/")
    parser.add_argument("--evidence-root", type=Path, default=COMMITTED_EVIDENCE)
    parser.add_argument("--release-version", default="1.0.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "evidence":
            evidence = args.evidence_root.resolve()
            require(evidence.is_dir(), f"evidence directory is missing: {evidence}")
            result = verify_common(evidence, None)
            verify_real(evidence, result)
        else:
            request = (args.request or (REAL_REQUEST if args.mode == "real" else PLAN_REQUEST)).resolve()
            require(request.is_file(), f"request is missing: {request}")
            workspace = safe_workspace(args.workspace or default_workspace(args.mode))
            result = (
                run_real(request, workspace, args.release_version)
                if args.mode == "real"
                else generate("plan", request, workspace, args.release_version)
            )
        print("presentation_result=")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        print("demo_status=passed")
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"demo_status=failed error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
