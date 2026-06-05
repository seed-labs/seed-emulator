#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def compose_exec(compose_file: Path, service: str, command: str, timeout: int = 45) -> Dict[str, object]:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "exec",
            "-T",
            service,
            "sh",
            "-lc",
            command,
        ],
        cwd=str(compose_file.parent),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "service": service,
        "command": command,
        "exit": result.returncode,
        "stdout": result.stdout[-1000:],
        "stderr": result.stderr[-1000:],
    }


def check(compose_file: Path, name: str, service: str, command: str) -> Dict[str, object]:
    result = compose_exec(compose_file, service, command)
    result["name"] = name
    result["status"] = "passed" if result["exit"] == 0 else "failed"
    return result


def main() -> int:
    example_dir = Path(os.environ.get("EXAMPLE_RUNNER_EXAMPLE_DIR", Path(__file__).parent)).resolve()
    compose_file = Path(
        os.environ.get("EXAMPLE_RUNNER_COMPOSE_FILE", example_dir / "output" / "docker-compose.yml")
    ).resolve()
    artifact_dir = os.environ.get("EXAMPLE_RUNNER_ARTIFACT_DIR")

    checks = [
        (
            "AS151 fetches AS152 web service",
            "hnode_151_web",
            "curl -fsS http://10.152.0.71 >/dev/null",
        ),
        (
            "AS152 fetches AS151 web service",
            "hnode_152_web",
            "curl -fsS http://10.151.0.71 >/dev/null",
        ),
        (
            "r1 has MPLS/LDP enabled on the internal transit network",
            "brdnode_2_r1",
            "test -s /mpls_ifaces.txt && grep -q '^net0$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        ),
        (
            "r2 is an MPLS non-edge router with both internal links enabled",
            "rnode_2_r2",
            "grep -q '^net0$' /mpls_ifaces.txt && grep -q '^net1$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        ),
        (
            "r3 is an MPLS non-edge router with both internal links enabled",
            "rnode_2_r3",
            "grep -q '^net1$' /mpls_ifaces.txt && grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        ),
        (
            "r4 has MPLS/LDP enabled on the internal transit network",
            "brdnode_2_r4",
            "test -s /mpls_ifaces.txt && grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        ),
    ]

    results: List[Dict[str, object]] = [
        check(compose_file, name, service, command) for name, service, command in checks
    ]
    summary = {
        "compose_file": str(compose_file),
        "results": results,
        "failures": [item["name"] for item in results if item["status"] == "failed"],
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    if artifact_dir:
        path = Path(artifact_dir) / "a02-mpls-runtime-test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
