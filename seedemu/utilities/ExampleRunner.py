#!/usr/bin/env python3

from __future__ import annotations

import argparse
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


class ExampleRunnerError(Exception):
    """Raised when an example runner configuration is invalid."""


class ExampleRunner:
    """Run standardized SEED Emulator examples from an example.yaml file.

    The runner is intentionally metadata-driven so CI, local developers, and
    agents can compile, build, start, probe, stop, and clean examples through
    the same lifecycle.
    """

    __manifest_path: Path
    __manifest: Dict[str, Any]
    __example_dir: Path
    __artifact_dir: Optional[Path]

    def __init__(self, manifest_path: Path, artifact_dir: Optional[Path] = None):
        self.__manifest_path = manifest_path.resolve()
        self.__example_dir = self.__manifest_path.parent
        self.__artifact_dir = artifact_dir.resolve() if artifact_dir is not None else None
        if self.__artifact_dir is not None:
            self.__artifact_dir.mkdir(parents=True, exist_ok=True)
        self.__manifest = self.__load_manifest()
        self.__validate_manifest()

    def clean(self) -> int:
        """Remove generated files declared in compile.clean."""

        clean_paths = self.__manifest.get("compile", {}).get("clean", [])
        for item in clean_paths:
            target = self.__resolve_example_path(item)
            self.__assert_inside_example_dir(target)
            if target.is_dir():
                shutil.rmtree(target)
                self.__log("removed directory {}".format(target))
            elif target.exists():
                target.unlink()
                self.__log("removed file {}".format(target))
        return 0

    def compile(self) -> int:
        """Compile the example and check declared outputs."""

        compile_cfg = self.__manifest.get("compile", {})
        if not compile_cfg.get("enabled", True):
            self.__log("compile is disabled for {}".format(self.example_id()))
            return 0

        script = self.__resolve_example_path(self.__manifest["script"])
        output = compile_cfg.get("output", "output")
        timeout = int(compile_cfg.get("timeout", 900))
        env = self.__merged_env(compile_cfg.get("env", {}))

        command = compile_cfg.get("command")
        if command is not None:
            cmd = self.__coerce_command(command)
        else:
            cmd = [sys.executable, script.name]
            if compile_cfg.get("standard_args", True):
                platform = self.__manifest.get("platform", "amd")
                cmd.extend(["--platform", str(platform), "--output", str(output)])
            cmd.extend(str(arg) for arg in compile_cfg.get("args", []))

        result = self.__run_command("compile", cmd, cwd=script.parent, env=env, timeout=timeout)
        if result.returncode != 0:
            return result.returncode

        missing = [
            item
            for item in compile_cfg.get("expected", [])
            if not self.__resolve_example_path(item).exists()
        ]
        if missing:
            self.__log("missing expected outputs: {}".format(", ".join(missing)))
            self.__write_json("compile-missing.json", {"missing": missing})
            return 1
        return 0

    def build(self) -> int:
        """Run docker compose build for the example."""

        build_cfg = self.__manifest.get("build", {})
        if not build_cfg.get("enabled", True):
            self.__log("build is disabled for {}".format(self.example_id()))
            return 0

        compose = self.compose_file()
        if not compose.is_file():
            self.__log("compose file not found: {}".format(compose))
            return 1

        timeout = int(build_cfg.get("timeout", 1800))
        cmd = ["docker", "compose", "-f", str(compose), "build"]
        return self.__run_command("build", cmd, cwd=compose.parent, env=self.__docker_env(), timeout=timeout).returncode

    def up(self) -> int:
        """Start the example with docker compose up -d."""

        compose = self.compose_file()
        if not compose.is_file():
            self.__log("compose file not found: {}".format(compose))
            return 1

        cmd = ["docker", "compose", "-f", str(compose), "up", "-d"]
        result = self.__run_command("up", cmd, cwd=compose.parent, env=self.__docker_env())
        if result.returncode != 0:
            return result.returncode
        return self.readiness()

    def down(self) -> int:
        """Stop the example and remove compose-created resources."""

        compose = self.compose_file()
        if not compose.exists():
            self.__log("compose file not found, skipping down: {}".format(compose))
            return 0

        cmd = ["docker", "compose", "-f", str(compose), "down", "--remove-orphans"]
        return self.__run_command("down", cmd, cwd=compose.parent, env=self.__docker_env()).returncode

    def readiness(self) -> int:
        """Run runtime.readiness probes."""

        runtime_cfg = self.__manifest.get("runtime", {})
        probes = runtime_cfg.get("readiness", [])
        if not probes:
            return 0
        return self.__run_probes("readiness", probes)

    def probe(self) -> int:
        """Run runtime probes declared under probes."""

        return self.__run_probes("probe", self.__manifest.get("probes", []))

    def all(self) -> int:
        """Run clean, compile, build, up, probe, and down."""

        status = 0
        try:
            for step in (self.clean, self.compile, self.build, self.up, self.probe):
                status = step()
                if status != 0:
                    break
        finally:
            down_status = self.down()
            if status == 0 and down_status != 0:
                status = down_status
        return status

    def compose_file(self) -> Path:
        """Return the compose file path for build/runtime operations."""

        runtime_cfg = self.__manifest.get("runtime", {})
        compose = runtime_cfg.get("compose")
        if compose is None:
            output = self.__manifest.get("compile", {}).get("output", "output")
            compose = str(Path(output) / "docker-compose.yml")
        return self.__resolve_example_path(compose)

    def example_id(self) -> str:
        """Return the stable example ID."""

        return str(self.__manifest["id"])

    def __run_probes(self, stage: str, probes: Sequence[Dict[str, Any]]) -> int:
        failures = []
        results = []
        for probe in probes:
            result = self.__run_probe_with_retries(probe)
            results.append(result)
            if result["status"] == "failed" and probe.get("required", True):
                failures.append(probe["name"])

        self.__write_json("{}-summary.json".format(stage), {"results": results, "failures": failures})
        if failures:
            self.__log("{} failures: {}".format(stage, ", ".join(failures)))
            return 1
        return 0

    def __run_probe_with_retries(self, probe: Dict[str, Any]) -> Dict[str, Any]:
        name = str(probe["name"])
        retries = int(probe.get("retries", 1))
        interval = float(probe.get("interval", 0))
        last_message = ""

        for attempt in range(1, retries + 1):
            self.__log("probe {} attempt {}/{}".format(name, attempt, retries))
            passed, message = self.__run_one_probe(probe)
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

    def __run_one_probe(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        probe_type = probe["type"]
        if probe_type == "exec":
            return self.__probe_exec(probe)
        if probe_type == "ping":
            command = "ping -c {} {}".format(int(probe.get("count", 3)), probe["target"])
            exec_probe = dict(probe)
            exec_probe["type"] = "exec"
            exec_probe["command"] = command
            exec_probe.setdefault("expect_exit", 0)
            return self.__probe_exec(exec_probe)
        if probe_type == "http":
            return self.__probe_http(probe)
        if probe_type == "tcp":
            return self.__probe_tcp(probe)
        if probe_type == "dns":
            return self.__probe_dns(probe)
        if probe_type == "compose-ps":
            return self.__probe_compose_ps(probe)
        if probe_type == "log-contains":
            return self.__probe_log_contains(probe)
        raise ExampleRunnerError("unknown probe type: {}".format(probe_type))

    def __probe_exec(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        cmd = [
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
        ]
        result = self.__run_command(
            "probe-{}".format(self.__slug(probe["name"])),
            cmd,
            cwd=compose.parent,
            env=self.__docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        expected = int(probe.get("expect_exit", 0))
        if result.returncode != expected:
            return False, "exit {}, expected {}".format(result.returncode, expected)

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        return self.__check_text_expectations(probe, stdout, stderr)

    def __probe_http(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        request = urllib.request.Request(
            str(probe["url"]),
            method=str(probe.get("method", "GET")),
            headers={str(k): str(v) for k, v in probe.get("headers", {}).items()},
        )
        try:
            with urllib.request.urlopen(request, timeout=int(probe.get("timeout", 10))) as response:
                body = response.read().decode("utf-8", errors="replace")
                expected_status = int(probe.get("expect_status", 200))
                if response.status != expected_status:
                    return False, "HTTP {}, expected {}".format(response.status, expected_status)
                return self.__check_body_expectations(probe, body)
        except Exception as exc:
            return False, str(exc)

    def __probe_tcp(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        try:
            with socket.create_connection(
                (str(probe["host"]), int(probe["port"])),
                timeout=int(probe.get("timeout", 10)),
            ):
                return True, "connected"
        except OSError as exc:
            return False, str(exc)

    def __probe_dns(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        query = str(probe["query"])
        record_type = str(probe.get("record_type", "A"))
        command = "getent hosts {}".format(query) if record_type in {"A", "AAAA"} else "nslookup -type={} {}".format(record_type, query)
        if probe.get("server"):
            command = "nslookup -type={} {} {}".format(record_type, query, probe["server"])

        if probe.get("service"):
            exec_probe = dict(probe)
            exec_probe["type"] = "exec"
            exec_probe["command"] = command
            exec_probe.setdefault("expect_exit", 0)
            return self.__probe_exec(exec_probe)

        result = self.__run_command(
            "probe-{}".format(self.__slug(probe["name"])),
            ["sh", "-lc", command],
            cwd=self.__example_dir,
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "DNS command exited {}".format(result.returncode)
        return self.__check_text_expectations(probe, result.stdout or "", result.stderr or "")

    def __probe_compose_ps(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        cmd = ["docker", "compose", "-f", str(compose), "ps", "--format", "json"]
        result = self.__run_command(
            "probe-{}".format(self.__slug(probe["name"])),
            cmd,
            cwd=compose.parent,
            env=self.__docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "docker compose ps exited {}".format(result.returncode)

        expected_services = {str(service) for service in probe.get("services", [])}
        if not expected_services:
            return True, "compose ps succeeded"

        running = set()
        for item in self.__parse_compose_ps_output(result.stdout or ""):
            name = item.get("Service") or item.get("Name")
            state = item.get("State") or item.get("Status")
            if name in expected_services and str(state).lower().startswith("running"):
                running.add(name)

        missing = sorted(expected_services - running)
        if missing:
            return False, "services not running: {}".format(", ".join(missing))
        return True, "all services running"

    def __probe_log_contains(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        compose = self.compose_file()
        cmd = ["docker", "compose", "-f", str(compose), "logs", str(probe["service"])]
        result = self.__run_command(
            "probe-{}".format(self.__slug(probe["name"])),
            cmd,
            cwd=compose.parent,
            env=self.__docker_env(),
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "docker compose logs exited {}".format(result.returncode)

        text = result.stdout or ""
        pattern = str(probe["pattern"])
        if probe.get("regex", False):
            return (True, "regex matched") if re.search(pattern, text) else (False, "regex did not match")
        return (True, "pattern found") if pattern in text else (False, "pattern not found")

    @staticmethod
    def __check_body_expectations(probe: Dict[str, Any], body: str) -> tuple[bool, str]:
        contains = probe.get("expect_body_contains")
        if contains is not None and str(contains) not in body:
            return False, "body does not contain {}".format(contains)
        regex = probe.get("expect_body_regex")
        if regex is not None and re.search(str(regex), body) is None:
            return False, "body regex did not match"
        return True, "body matched"

    @staticmethod
    def __check_text_expectations(probe: Dict[str, Any], stdout: str, stderr: str) -> tuple[bool, str]:
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

    def __run_command(
        self,
        name: str,
        cmd: Sequence[str],
        *,
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess[str]:
        self.__log("cwd={} cmd={}".format(cwd, " ".join(cmd)))
        result = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        self.__write_command_log(name, cmd, cwd, result)
        return result

    def __load_manifest(self) -> Dict[str, Any]:
        if not self.__manifest_path.is_file():
            raise ExampleRunnerError("manifest does not exist: {}".format(self.__manifest_path))
        try:
            import yaml
        except ImportError as exc:
            raise ExampleRunnerError("PyYAML is required to read example manifests") from exc

        data = yaml.safe_load(self.__manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ExampleRunnerError("manifest must be a YAML mapping")
        return data

    def __validate_manifest(self) -> None:
        if not self.__manifest.get("id"):
            raise ExampleRunnerError("example manifest must define id")
        if not self.__manifest.get("script"):
            raise ExampleRunnerError("example manifest must define script")
        script = self.__resolve_example_path(self.__manifest["script"])
        if not script.is_file():
            raise ExampleRunnerError("example script does not exist: {}".format(script))

        for probe in self.__manifest.get("probes", []):
            self.__validate_probe(probe)
        for probe in self.__manifest.get("runtime", {}).get("readiness", []):
            self.__validate_probe(probe)

    @staticmethod
    def __validate_probe(probe: Dict[str, Any]) -> None:
        if "name" not in probe or "type" not in probe:
            raise ExampleRunnerError("each probe must define name and type")
        probe_type = probe["type"]
        required = {
            "exec": ["service", "command"],
            "ping": ["service", "target"],
            "http": ["url"],
            "tcp": ["host", "port"],
            "dns": ["query"],
            "compose-ps": [],
            "log-contains": ["service", "pattern"],
        }.get(probe_type)
        if required is None:
            raise ExampleRunnerError("unknown probe type: {}".format(probe_type))
        missing = [field for field in required if field not in probe]
        if missing:
            raise ExampleRunnerError(
                "probe {} missing fields: {}".format(probe.get("name", "<unnamed>"), ", ".join(missing))
            )

    def __resolve_example_path(self, value: Any) -> Path:
        path = Path(str(value))
        if path.is_absolute():
            return path
        return (self.__example_dir / path).resolve()

    def __assert_inside_example_dir(self, target: Path) -> None:
        base = self.__example_dir.resolve()
        if target != base and base not in target.parents:
            raise ExampleRunnerError("refusing to operate outside example directory: {}".format(target))

    def __write_command_log(
        self,
        name: str,
        cmd: Sequence[str],
        cwd: Path,
        result: subprocess.CompletedProcess[str],
    ) -> None:
        if self.__artifact_dir is None:
            return
        log_path = self.__artifact_dir / "logs" / "{}.log".format(self.__slug(name))
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

    def __write_json(self, name: str, data: Dict[str, Any]) -> None:
        if self.__artifact_dir is None:
            return
        path = self.__artifact_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def __coerce_command(command: Any) -> List[str]:
        if isinstance(command, list):
            return [str(item) for item in command]
        raise ExampleRunnerError("command must be a list of arguments")

    @staticmethod
    def __merged_env(extra: Dict[str, Any]) -> Dict[str, str]:
        env = dict(os.environ)
        env.update({str(k): str(v) for k, v in extra.items()})
        return env

    @staticmethod
    def __parse_compose_ps_output(output: str) -> List[Dict[str, Any]]:
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
    def __docker_env() -> Dict[str, str]:
        env = ExampleRunner.__merged_env({})
        env.setdefault("DOCKER_BUILDKIT", "0")
        env.setdefault("COMPOSE_BAKE", "false")
        env.setdefault("COMPOSE_PARALLEL_LIMIT", "1")
        return env

    @staticmethod
    def __slug(value: Any) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "check"

    @staticmethod
    def __log(message: str) -> None:
        print("[example-runner] {}".format(message))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a standardized SEED Emulator example.")
    parser.add_argument(
        "command",
        choices=["clean", "compile", "build", "up", "readiness", "probe", "down", "all"],
    )
    parser.add_argument("manifest", type=Path, help="Path to an example.yaml file.")
    parser.add_argument("--artifact-dir", type=Path, help="Optional directory for command logs and summaries.")
    args = parser.parse_args(argv)

    runner = ExampleRunner(args.manifest, artifact_dir=args.artifact_dir)
    commands = {
        "clean": runner.clean,
        "compile": runner.compile,
        "build": runner.build,
        "up": runner.up,
        "readiness": runner.readiness,
        "probe": runner.probe,
        "down": runner.down,
        "all": runner.all,
    }
    return commands[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
