#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class TestRunnerError(Exception):
    """Raised when a test runner manifest or lifecycle operation is invalid."""


class TestRunner:
    """Base runner for standardized emulation testing.

    This class owns generic lifecycle behavior: loading manifests, running
    commands, writing artifacts, starting/stopping Docker Compose environments,
    retrying probes, and executing custom test programs. Domain-specific
    runners extend probe handlers and manifest validation.
    """

    runner_name = "generic"
    probe_handlers: Dict[str, str] = {
        "exec": "probe_exec",
        "http": "probe_http",
        "tcp": "probe_tcp",
        "compose-ps": "probe_compose_ps",
        "log-contains": "probe_log_contains",
    }

    manifest_path: Path
    manifest: Dict[str, Any]
    emulation_dir: Path
    artifact_dir: Optional[Path]

    def __init__(self, manifest_path: Path, artifact_dir: Optional[Path] = None):
        self.manifest_path = manifest_path.resolve()
        self.emulation_dir = self.manifest_path.parent
        self.artifact_dir = artifact_dir.resolve() if artifact_dir is not None else None
        if self.artifact_dir is not None:
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = self.load_manifest()
        self.validate_manifest()

    def clean(self) -> int:
        """Remove generated files declared in compile.clean."""

        clean_paths = self.manifest.get("compile", {}).get("clean", [])
        for item in clean_paths:
            target = self.resolve_emulation_path(item)
            self.assert_inside_emulation_dir(target)
            if target.is_dir():
                shutil.rmtree(target)
                self.log("removed directory {}".format(target))
            elif target.exists():
                target.unlink()
                self.log("removed file {}".format(target))
        return 0

    def compile(self) -> int:
        """Compile the emulation and check declared outputs."""

        compile_cfg = self.manifest.get("compile", {})
        if not compile_cfg.get("enabled", True):
            self.log("compile is disabled for {}".format(self.emulation_id()))
            return 0

        script = self.resolve_emulation_path(self.manifest["script"])
        output = compile_cfg.get("output", "output")
        timeout = int(compile_cfg.get("timeout", 900))
        env = self.merged_env(compile_cfg.get("env", {}))

        command = compile_cfg.get("command")
        if command is not None:
            cmd = self.coerce_command(command)
        else:
            cmd = [sys.executable, script.name]
            if compile_cfg.get("standard_args", True):
                platform = self.manifest.get("platform", "amd")
                cmd.extend(["--platform", str(platform), "--output", str(output)])
            cmd.extend(str(arg) for arg in compile_cfg.get("args", []))

        result = self.run_command("compile", cmd, cwd=script.parent, env=env, timeout=timeout)
        if result.returncode != 0:
            return result.returncode

        missing = [
            item
            for item in compile_cfg.get("expected", [])
            if not self.resolve_emulation_path(item).exists()
        ]
        if missing:
            self.log("missing expected outputs: {}".format(", ".join(missing)))
            self.write_json("compile-missing.json", {"missing": missing})
            return 1
        return 0

    def build(self) -> int:
        """Run Docker Compose build for the emulation."""

        build_cfg = self.manifest.get("build", {})
        if not build_cfg.get("enabled", True):
            self.log("build is disabled for {}".format(self.emulation_id()))
            return 0

        compose = self.compose_file()
        if not compose.is_file():
            self.log("compose file not found: {}".format(compose))
            return 1

        cmd = ["docker", "compose", "-f", str(compose), "build"]
        return self.run_command(
            "build",
            cmd,
            cwd=compose.parent,
            env=self.docker_env(),
            timeout=int(build_cfg.get("timeout", 1800)),
        ).returncode

    def up(self) -> int:
        """Start the emulation with Docker Compose and run readiness probes."""

        compose = self.compose_file()
        if not compose.is_file():
            self.log("compose file not found: {}".format(compose))
            return 1

        cmd = ["docker", "compose", "-f", str(compose), "up", "-d"]
        result = self.run_command("up", cmd, cwd=compose.parent, env=self.docker_env())
        if result.returncode != 0:
            return result.returncode
        return self.readiness()

    def down(self) -> int:
        """Stop the emulation and remove Compose-created resources."""

        compose = self.compose_file()
        if not compose.exists():
            self.log("compose file not found, skipping down: {}".format(compose))
            return 0

        cmd = ["docker", "compose", "-f", str(compose), "down", "--remove-orphans"]
        return self.run_command("down", cmd, cwd=compose.parent, env=self.docker_env()).returncode

    def readiness(self) -> int:
        """Run runtime.readiness probes."""

        probes = self.manifest.get("runtime", {}).get("readiness", [])
        if not probes:
            return 0
        return self.run_probes("readiness", probes)

    def probe(self) -> int:
        """Run probes declared under probes."""

        return self.run_probes("probe", self.manifest.get("probes", []))

    def test(self) -> int:
        """Run custom test programs declared under test_programs."""

        return self.run_test_programs(self.manifest.get("test_programs", []))

    def all(self) -> int:
        """Run clean, compile, build, up, probe, test, and down."""

        status = 0
        try:
            for step in (self.clean, self.compile, self.build, self.up, self.probe, self.test):
                status = step()
                if status != 0:
                    break
        finally:
            down_status = self.down()
            if status == 0 and down_status != 0:
                status = down_status
        return status

    def compose_file(self) -> Path:
        """Return the Compose file path for build/runtime operations."""

        compose = self.manifest.get("runtime", {}).get("compose")
        if compose is None:
            output = self.manifest.get("compile", {}).get("output", "output")
            compose = str(Path(output) / "docker-compose.yml")
        return self.resolve_emulation_path(compose)

    def emulation_id(self) -> str:
        """Return the stable emulation ID from the manifest."""

        return str(self.manifest["id"])

    def run_probes(self, stage: str, probes: Sequence[Dict[str, Any]]) -> int:
        failures = []
        results = []
        for probe in probes:
            result = self.run_probe_with_retries(probe)
            results.append(result)
            self.log("{} {}: {}".format(result["status"], result["name"], result.get("message", "")))
            if result["status"] == "failed" and probe.get("required", True):
                failures.append(probe["name"])

        self.write_json("{}-summary.json".format(stage), {"results": results, "failures": failures})
        if failures:
            self.log("{} failures: {}".format(stage, ", ".join(failures)))
            return 1
        return 0

    def run_test_programs(self, tests: Sequence[Dict[str, Any]]) -> int:
        failures = []
        results = []
        for test in tests:
            name = str(test["name"])
            result = self.run_command(
                "test-{}".format(self.slug(name)),
                self.test_command(test),
                cwd=self.emulation_dir,
                env=self.test_env(test.get("env", {})),
                timeout=int(test.get("timeout", 300)),
            )
            expected = int(test.get("expect_exit", 0))
            status = "passed" if result.returncode == expected else "failed"
            message = "exit {}, expected {}".format(result.returncode, expected)
            self.log("{} {}: {}".format(status, name, message))
            results.append(
                {
                    "name": name,
                    "status": status,
                    "exit": result.returncode,
                    "expected_exit": expected,
                    "message": message,
                }
            )
            if status == "failed" and test.get("required", True):
                failures.append(name)

        self.write_json("test-summary.json", {"results": results, "failures": failures})
        if failures:
            self.log("test failures: {}".format(", ".join(failures)))
            return 1
        return 0

    def run_probe_with_retries(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        name = str(probe["name"])
        retries = int(probe.get("retries", 1))
        interval = float(probe.get("interval", 0))
        last_message = ""

        for attempt in range(1, retries + 1):
            self.log("probe {} attempt {}/{}".format(name, attempt, retries))
            passed, message = self.run_one_probe(probe)
            if passed:
                return {
                    "name": name,
                    "type": probe["type"],
                    "status": "passed",
                    "attempts": attempt,
                    "message": message,
                }
            last_message = message
            if attempt < retries and interval > 0:
                time.sleep(interval)

        status = "failed" if probe.get("required", True) else "skipped"
        return {
            "name": name,
            "type": probe["type"],
            "status": status,
            "attempts": retries,
            "message": last_message,
        }

    def run_one_probe(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        probe_type = str(probe["type"])
        handler_name = self.probe_handlers.get(probe_type)
        if handler_name is None:
            raise TestRunnerError("unknown probe type for {} runner: {}".format(self.runner_name, probe_type))
        return getattr(self, handler_name)(probe)

    def probe_exec(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        result = self.run_command(
            "probe-{}".format(self.slug(probe["name"])),
            [
                "docker",
                "compose",
                "-f",
                str(compose),
                "exec",
                "-T",
                str(probe["service"]),
                "sh",
                "-lc",
                str(probe["command"]),
            ],
            cwd=compose.parent,
            env=self.docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        expected = int(probe.get("expect_exit", 0))
        if result.returncode != expected:
            return False, "exit {}, expected {}".format(result.returncode, expected)
        return self.check_text_expectations(probe, result.stdout or "", result.stderr or "")

    def probe_http(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        request = urllib.request.Request(
            str(probe["url"]),
            method=str(probe.get("method", "GET")),
            headers={str(k): str(v) for k, v in probe.get("headers", {}).items()},
        )
        data = None
        if "body" in probe:
            data = str(probe["body"]).encode("utf-8")

        try:
            with urllib.request.urlopen(request, data=data, timeout=int(probe.get("timeout", 10))) as response:
                body = response.read().decode("utf-8", errors="replace")
                expected_status = int(probe.get("expect_status", 200))
                if response.status != expected_status:
                    return False, "HTTP {}, expected {}".format(response.status, expected_status)
                return self.check_body_expectations(probe, body)
        except Exception as exc:
            return False, str(exc)

    def probe_tcp(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        try:
            with socket.create_connection(
                (str(probe["host"]), int(probe["port"])),
                timeout=int(probe.get("timeout", 10)),
            ):
                return True, "connected"
        except OSError as exc:
            return False, str(exc)

    def probe_compose_ps(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        result = self.run_command(
            "probe-{}".format(self.slug(probe["name"])),
            ["docker", "compose", "-f", str(compose), "ps", "--format", "json"],
            cwd=compose.parent,
            env=self.docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "docker compose ps exited {}".format(result.returncode)

        expected_services = {str(service) for service in probe.get("services", [])}
        if not expected_services:
            return True, "compose ps succeeded"

        running = set()
        observed = []
        for item in self.parse_compose_ps_output(result.stdout or ""):
            name = item.get("Service") or item.get("Name")
            state = item.get("State") or item.get("Status")
            observed.append("{}={}".format(name, state))
            state_text = str(state).lower()
            if name in expected_services and (
                state_text.startswith("running") or state_text.startswith("up")
            ):
                running.add(name)

        missing = sorted(expected_services - running)
        if missing:
            return False, "services not running: {}; observed: {}".format(
                ", ".join(missing),
                ", ".join(observed) or "<none>",
            )
        return True, "all services running"

    def probe_log_contains(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        result = self.run_command(
            "probe-{}".format(self.slug(probe["name"])),
            ["docker", "compose", "-f", str(compose), "logs", str(probe["service"])],
            cwd=compose.parent,
            env=self.docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "docker compose logs exited {}".format(result.returncode)

        text = result.stdout or ""
        pattern = str(probe["pattern"])
        if probe.get("regex", False):
            return (True, "regex matched") if re.search(pattern, text) else (False, "regex did not match")
        return (True, "pattern found") if pattern in text else (False, "pattern not found")

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.is_file():
            raise TestRunnerError("manifest does not exist: {}".format(self.manifest_path))
        try:
            import yaml
        except ImportError as exc:
            raise TestRunnerError("PyYAML is required to read test manifests") from exc

        data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TestRunnerError("manifest must be a YAML mapping")
        return data

    def validate_manifest(self) -> None:
        if not self.manifest.get("id"):
            raise TestRunnerError("test manifest must define id")
        if not self.manifest.get("script"):
            raise TestRunnerError("test manifest must define script")
        script = self.resolve_emulation_path(self.manifest["script"])
        if not script.is_file():
            raise TestRunnerError("emulation script does not exist: {}".format(script))

        for probe in self.manifest.get("probes", []):
            self.validate_probe(probe)
        for probe in self.manifest.get("runtime", {}).get("readiness", []):
            self.validate_probe(probe)
        for test in self.manifest.get("test_programs", []):
            self.validate_test_program(test)

    def validate_probe(self, probe: Dict[str, Any]) -> None:
        if "name" not in probe or "type" not in probe:
            raise TestRunnerError("each probe must define name and type")
        required = self.required_probe_fields(str(probe["type"]))
        if required is None:
            raise TestRunnerError("unknown probe type for {} runner: {}".format(self.runner_name, probe["type"]))
        missing = [field for field in required if field not in probe]
        if missing:
            raise TestRunnerError(
                "probe {} missing fields: {}".format(probe.get("name", "<unnamed>"), ", ".join(missing))
            )

    def validate_test_program(self, test: Dict[str, Any]) -> None:
        if "name" not in test:
            raise TestRunnerError("each test program must define name")
        if "script" not in test and "command" not in test:
            raise TestRunnerError(
                "test program {} must define script or command".format(test.get("name", "<unnamed>"))
            )
        if "script" in test:
            script = self.resolve_emulation_path(test["script"])
            if not script.is_file():
                raise TestRunnerError("test program script does not exist: {}".format(script))

    def required_probe_fields(self, probe_type: str) -> Optional[List[str]]:
        return {
            "exec": ["service", "command"],
            "http": ["url"],
            "tcp": ["host", "port"],
            "compose-ps": [],
            "log-contains": ["service", "pattern"],
        }.get(probe_type)

    def resolve_emulation_path(self, value: Any) -> Path:
        path = Path(str(value))
        if path.is_absolute():
            return path
        return (self.emulation_dir / path).resolve()

    def test_command(self, test: Dict[str, Any]) -> List[str]:
        if "command" in test:
            return self.coerce_command(test["command"])

        script = self.resolve_emulation_path(test["script"])
        cmd = [sys.executable, str(script)]
        cmd.extend(str(arg) for arg in test.get("args", []))
        return cmd

    def assert_inside_emulation_dir(self, target: Path) -> None:
        base = self.emulation_dir.resolve()
        if target != base and base not in target.parents:
            raise TestRunnerError("refusing to operate outside emulation directory: {}".format(target))

    def run_command(
        self,
        name: str,
        cmd: Sequence[str],
        *,
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess[str]:
        self.log("cwd={} cmd={}".format(cwd, " ".join(cmd)))
        result = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        self.write_command_log(name, cmd, cwd, result)
        return result

    def write_command_log(
        self,
        name: str,
        cmd: Sequence[str],
        cwd: Path,
        result: subprocess.CompletedProcess[str],
    ) -> None:
        if self.artifact_dir is None:
            return
        log_path = self.artifact_dir / "logs" / "{}.log".format(self.slug(name))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "COMMAND: {}\nCWD: {}\nEXIT: {}\n\nSTDOUT:\n{}\n\nSTDERR:\n{}\n".format(
                " ".join(cmd),
                cwd,
                result.returncode,
                result.stdout,
                result.stderr,
            ),
            encoding="utf-8",
        )

    def write_json(self, name: str, data: Dict[str, Any]) -> None:
        if self.artifact_dir is None:
            return
        path = self.artifact_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_env(self, extra: Dict[str, Any]) -> Dict[str, str]:
        env = self.docker_env()
        env.update(
            {
                "TEST_RUNNER_NAME": self.runner_name,
                "TEST_RUNNER_EMULATION_ID": self.emulation_id(),
                "TEST_RUNNER_EMULATION_DIR": str(self.emulation_dir),
                "TEST_RUNNER_MANIFEST": str(self.manifest_path),
                "TEST_RUNNER_COMPOSE_FILE": str(self.compose_file()),
                "TEST_RUNNER_ARTIFACT_DIR": str(self.artifact_dir or ""),
                "EXAMPLE_RUNNER_EXAMPLE_ID": self.emulation_id(),
                "EXAMPLE_RUNNER_EXAMPLE_DIR": str(self.emulation_dir),
                "EXAMPLE_RUNNER_MANIFEST": str(self.manifest_path),
                "EXAMPLE_RUNNER_COMPOSE_FILE": str(self.compose_file()),
                "EXAMPLE_RUNNER_ARTIFACT_DIR": str(self.artifact_dir or ""),
            }
        )
        env.update({str(k): str(v) for k, v in extra.items()})
        return env

    @staticmethod
    def coerce_command(command: Any) -> List[str]:
        if isinstance(command, list):
            return [str(item) for item in command]
        raise TestRunnerError("command must be a list of arguments")

    @staticmethod
    def merged_env(extra: Dict[str, Any]) -> Dict[str, str]:
        env = dict(os.environ)
        env.update({str(k): str(v) for k, v in extra.items()})
        return env

    @staticmethod
    def docker_env() -> Dict[str, str]:
        env = TestRunner.merged_env({})
        env.setdefault("DOCKER_BUILDKIT", "0")
        env.setdefault("COMPOSE_BAKE", "false")
        env.setdefault("COMPOSE_PARALLEL_LIMIT", "1")
        return env

    @staticmethod
    def parse_compose_ps_output(output: str) -> List[Dict[str, Any]]:
        output = output.strip()
        if not output:
            return []

        try:
            data = json.loads(output)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass

        items = []
        for line in output.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                items.append(item)
        return items

    @staticmethod
    def check_body_expectations(probe: Dict[str, Any], body: str) -> tuple[bool, str]:
        contains = probe.get("expect_body_contains")
        if contains is not None and str(contains) not in body:
            return False, "body does not contain {}".format(contains)
        regex = probe.get("expect_body_regex")
        if regex is not None and re.search(str(regex), body) is None:
            return False, "body regex did not match"
        return True, "body matched"

    @staticmethod
    def check_text_expectations(probe: Dict[str, Any], stdout: str, stderr: str) -> tuple[bool, str]:
        stdout_contains = probe.get("expect_stdout_contains")
        if stdout_contains is not None and str(stdout_contains) not in stdout:
            return False, "stdout does not contain {}".format(stdout_contains)
        stdout_regex = probe.get("expect_stdout_regex") or probe.get("expect_answer_regex")
        if stdout_regex is not None and re.search(str(stdout_regex), stdout) is None:
            return False, "stdout regex did not match"
        stderr_contains = probe.get("expect_stderr_contains")
        if stderr_contains is not None and str(stderr_contains) not in stderr:
            return False, "stderr does not contain {}".format(stderr_contains)
        answer = probe.get("expect_answer")
        if answer is not None and str(answer) not in stdout:
            return False, "answer not found in stdout"
        return True, "text matched"

    @staticmethod
    def slug(value: Any) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "check"

    @staticmethod
    def log(message: str) -> None:
        print("[test-runner] {}".format(message))
