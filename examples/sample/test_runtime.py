#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def run_compose_exec(compose_file: Path, service: str, command: str, timeout: int = 45) -> Dict[str, object]:
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


def main() -> int:
    example_dir = Path(os.environ.get("EXAMPLE_RUNNER_EXAMPLE_DIR", Path(__file__).parent)).resolve()
    compose_file = Path(
        os.environ.get("EXAMPLE_RUNNER_COMPOSE_FILE", example_dir / "output" / "docker-compose.yml")
    ).resolve()
    artifact_dir = os.environ.get("EXAMPLE_RUNNER_ARTIFACT_DIR")

    checks = [
        {
            "name": "AS151 fetches AS150 web service",
            "service": "hnode_151_web",
            "command": "curl -fsS http://10.150.0.71 >/dev/null",
        },
        {
            "name": "AS152 fetches AS151 web service",
            "service": "hnode_152_web",
            "command": "curl -fsS http://10.151.0.71 >/dev/null",
        },
        {
            "name": "AS150 reaches AS152 by ICMP",
            "service": "hnode_150_web",
            "command": "ping -c 3 10.152.0.71 >/dev/null",
        },
    ]

    results: List[Dict[str, object]] = []
    for check in checks:
        result = run_compose_exec(compose_file, str(check["service"]), str(check["command"]))
        result["name"] = check["name"]
        result["status"] = "passed" if result["exit"] == 0 else "failed"
        results.append(result)

    summary = {
        "compose_file": str(compose_file),
        "results": results,
        "failures": [item["name"] for item in results if item["status"] == "failed"],
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    if artifact_dir:
        path = Path(artifact_dir) / "sample-custom-runtime-test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
