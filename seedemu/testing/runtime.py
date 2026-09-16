#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

try:
    from .compose import docker_compose_command
except ImportError:
    from compose import docker_compose_command


ASN_LABEL = "org.seedsecuritylabs.seedemu.meta.asn"
NODE_LABEL = "org.seedsecuritylabs.seedemu.meta.nodename"
ADDRESS_LABEL = "org.seedsecuritylabs.seedemu.meta.net.0.address"


@dataclass(frozen=True)
class ComposeService:
    """A generated Docker Compose service discovered from SEED Emulator labels."""

    name: str
    address: str
    labels: Dict[str, object]


class ComposeRuntimeTest:
    """Helper for custom runtime tests launched by TestRunner.

    The lifecycle runner already knows how to compile, build, start, and stop an
    emulation. This helper is for example-specific test programs that need to
    inspect generated Compose metadata and run commands inside containers.
    """

    def __init__(self, test_file: str | Path):
        self.test_file = Path(test_file).resolve()
        self.example_dir = Path(
            os.environ.get("TEST_RUNNER_EMULATION_DIR")
            or os.environ.get("EXAMPLE_RUNNER_EXAMPLE_DIR")
            or self.test_file.parent
        ).resolve()
        self.compose_file = Path(
            os.environ.get("TEST_RUNNER_COMPOSE_FILE")
            or os.environ.get("EXAMPLE_RUNNER_COMPOSE_FILE")
            or self.example_dir / "output" / "docker-compose.yml"
        ).resolve()
        artifact_dir = os.environ.get("TEST_RUNNER_ARTIFACT_DIR") or os.environ.get("EXAMPLE_RUNNER_ARTIFACT_DIR")
        self.artifact_dir = Path(artifact_dir).resolve() if artifact_dir else None
        self.compose = self.load_compose()
        self.results: List[Dict[str, object]] = []

    def load_compose(self) -> Dict[str, object]:
        with self.compose_file.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def find_service(self, asn: int, node: str) -> Optional[ComposeService]:
        """Find a generated service by stable SEED Emulator metadata labels."""

        for name, service in self.compose.get("services", {}).items():
            labels = service.get("labels", {})
            if str(labels.get(ASN_LABEL)) == str(asn) and labels.get(NODE_LABEL) == node:
                address = str(labels.get(ADDRESS_LABEL, "")).split("/", 1)[0]
                return ComposeService(name=str(name), address=address, labels=dict(labels))
        return None

    def require_service(self, asn: int, node: str, description: Optional[str] = None) -> Optional[ComposeService]:
        """Record a structural check and return the discovered service, if any."""

        service = self.find_service(asn, node)
        label = description or "AS{} {} is generated".format(asn, node)
        if service is None:
            self.structural_check(label, False, "service for AS{} node {} not found".format(asn, node))
        else:
            self.structural_check(label, True, "found {}".format(service.name))
        return service

    def exec(self, service: ComposeService | str, command: str, timeout: int = 45) -> Dict[str, object]:
        service_name = service.name if isinstance(service, ComposeService) else str(service)
        result = subprocess.run(
            docker_compose_command()
            + ["-f", str(self.compose_file), "exec", "-T", service_name, "sh", "-lc", command],
            cwd=str(self.compose_file.parent),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "service": service_name,
            "command": command,
            "exit": result.returncode,
            "stdout": result.stdout[-1000:],
            "stderr": result.stderr[-1000:],
        }

    def exec_check(
        self,
        name: str,
        service: ComposeService | str,
        command: str,
        retries: int = 20,
        interval: int = 3,
        timeout: int = 45,
    ) -> Dict[str, object]:
        """Run a command with retries and append the check result."""

        result: Dict[str, object] = {}
        for attempt in range(1, retries + 1):
            result = self.exec(service, command, timeout=timeout)
            if result["exit"] == 0:
                break
            if attempt < retries:
                time.sleep(interval)
        result["name"] = name
        result["attempts"] = attempt
        result["status"] = "passed" if result["exit"] == 0 else "failed"
        self.results.append(result)
        return result

    def structural_check(self, name: str, passed: bool, message: str) -> Dict[str, object]:
        result = {
            "name": name,
            "service": "<output>",
            "command": "inspect generated docker-compose.yml",
            "exit": 0 if passed else 1,
            "stdout": message,
            "stderr": "",
            "status": "passed" if passed else "failed",
        }
        self.results.append(result)
        return result

    def summary(self) -> Dict[str, object]:
        return {
            "compose_file": str(self.compose_file),
            "results": self.results,
            "failures": [item["name"] for item in self.results if item["status"] == "failed"],
        }

    def write_summary(self, filename: str) -> Dict[str, object]:
        summary = self.summary()
        print(json.dumps(summary, indent=2, sort_keys=True))
        if self.artifact_dir:
            path = self.artifact_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def exit_code(self) -> int:
        return 1 if self.summary()["failures"] else 0
