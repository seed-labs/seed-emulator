#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).with_name("feature_manifest.json")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "check"


def _json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != 1:
        errors.append("manifest schema must be 1")

    features = manifest.get("features", {})
    unit_groups = manifest.get("unit_groups", {})
    runtime_groups = manifest.get("runtime_groups", {})
    examples = manifest.get("examples", {})
    required_features = {
        "ipv4-default",
        "ipv6-core",
        "routing-bird-frr",
        "exabgp-service",
        "looking-glass",
        "dns-endpoint",
        "legacy-guard",
    }
    missing = sorted(required_features.difference(features))
    if missing:
        errors.append(f"missing required feature declarations: {', '.join(missing)}")

    for feature_id, feature in features.items():
        for group_id in feature.get("unit_groups", []):
            if group_id not in unit_groups:
                errors.append(f"feature {feature_id} references missing unit group {group_id}")
        for group_id in feature.get("runtime_groups", []):
            if group_id not in runtime_groups:
                errors.append(f"feature {feature_id} references missing runtime group {group_id}")
        for example_id in feature.get("compile_examples", []):
            if example_id not in examples:
                errors.append(f"feature {feature_id} references missing compile example {example_id}")
        for example_id in feature.get("build_examples", []):
            if example_id not in examples:
                errors.append(f"feature {feature_id} references missing build example {example_id}")

    for example_id, example in examples.items():
        script = REPO_ROOT / example.get("script", "")
        if not script.is_file():
            errors.append(f"example {example_id} script does not exist: {_rel(script)}")
        for expected in example.get("expected", []):
            if Path(expected).is_absolute():
                errors.append(f"example {example_id} expected path must be relative: {expected}")
        for clean in example.get("clean", []):
            if Path(clean).is_absolute():
                errors.append(f"example {example_id} clean path must be relative: {clean}")
    return errors


def feature_coverage(manifest: dict[str, Any]) -> dict[str, Any]:
    features = {}
    for feature_id, feature in sorted(manifest["features"].items()):
        features[feature_id] = {
            "status": feature["status"],
            "description": feature.get("description", ""),
            "unit_groups": feature.get("unit_groups", []),
            "compile_examples": feature.get("compile_examples", []),
            "build_examples": feature.get("build_examples", []),
            "runtime_groups": feature.get("runtime_groups", []),
            "notes": feature.get("notes", ""),
        }
    return {
        "schema": manifest["schema"],
        "generated_by": "tests/ci/run_ci.py",
        "features": features,
    }


def _write_junit(stage: str, checks: list[dict[str, Any]], path: Path) -> None:
    tests = len(checks)
    failures = sum(1 for check in checks if check["status"] == "failed")
    skipped = sum(1 for check in checks if check["status"] == "skipped")
    suite = ET.Element(
        "testsuite",
        {
            "name": f"seedemu-ci-{stage}",
            "tests": str(tests),
            "failures": str(failures),
            "errors": "0",
            "skipped": str(skipped),
            "time": f"{sum(float(check.get('duration_s', 0.0)) for check in checks):.3f}",
        },
    )
    for check in checks:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": f"seedemu.ci.{stage}",
                "name": check["name"],
                "time": f"{float(check.get('duration_s', 0.0)):.3f}",
            },
        )
        if check["status"] == "failed":
            failure = ET.SubElement(
                case,
                "failure",
                {
                    "message": check.get("message", "check failed"),
                    "type": "CommandFailure",
                },
            )
            failure.text = check.get("details", "")
        elif check["status"] == "skipped":
            skipped_node = ET.SubElement(case, "skipped", {"message": check.get("message", "skipped")})
            skipped_node.text = check.get("details", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def _stage_result(stage: str, checks: list[dict[str, Any]], artifact_dir: Path) -> int:
    summary = {
        "stage": stage,
        "status": "failed" if any(check["status"] == "failed" for check in checks) else "passed",
        "checks": checks,
    }
    _json_dump(artifact_dir / "ci-summary.json", summary)
    _write_junit(stage, checks, artifact_dir / "junit.xml")

    print(f"[seed-ci] stage={stage} status={summary['status']} artifact_dir={_rel(artifact_dir)}")
    for check in checks:
        print(
            "[seed-ci] "
            f"{check['status']}: {check['name']} "
            f"log={check.get('log_path', '')}"
        )
        if check["status"] == "failed":
            command = check.get("command")
            if command:
                print(f"[seed-ci] failed-command: {' '.join(command)}")
            details = (check.get("stderr_tail") or check.get("details") or "").strip()
            if details:
                print("[seed-ci] failure-tail:")
                print(_tail(details, limit=1200))
    return 1 if summary["status"] == "failed" else 0


def _run_command(
    name: str,
    cmd: list[str],
    artifact_dir: Path,
    *,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    start = time.monotonic()
    log_path = artifact_dir / "logs" / f"{_slug(name)}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        duration = time.monotonic() - start
        log_path.write_text(
            "COMMAND: {}\nCWD: {}\nEXIT: {}\n\nSTDOUT:\n{}\n\nSTDERR:\n{}\n".format(
                " ".join(cmd),
                _rel(cwd),
                result.returncode,
                result.stdout,
                result.stderr,
            ),
            encoding="utf-8",
        )
        status = "passed" if result.returncode == 0 else "failed"
        return {
            "name": name,
            "status": status,
            "command": cmd,
            "cwd": _rel(cwd),
            "returncode": result.returncode,
            "duration_s": duration,
            "log_path": _rel(log_path),
            "stdout_tail": _tail(result.stdout),
            "stderr_tail": _tail(result.stderr),
            "message": "command failed" if status == "failed" else "command passed",
            "details": _tail(result.stdout + "\n" + result.stderr),
        }
    except Exception as exc:  # pragma: no cover - defensive diagnostics for CI infrastructure failures.
        duration = time.monotonic() - start
        details = traceback.format_exc()
        log_path.write_text(details, encoding="utf-8")
        return {
            "name": name,
            "status": "failed",
            "command": cmd,
            "cwd": _rel(cwd),
            "returncode": None,
            "duration_s": duration,
            "log_path": _rel(log_path),
            "message": str(exc),
            "details": details,
        }


def _git_diff_check_command() -> list[str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        candidates = [f"origin/{base_ref}", base_ref]
        for candidate in candidates:
            probe = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if probe.returncode == 0:
                return ["git", "diff", "--check", f"{candidate}...HEAD"]
    return ["git", "diff", "--check"]


def _example_ids(manifest: dict[str, Any], key: str) -> list[str]:
    ids: list[str] = []
    for example_id, example in manifest["examples"].items():
        if example.get(key):
            ids.append(example_id)
    return ids


def _pythonpath_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPO_ROOT) if not existing else f"{REPO_ROOT}:{existing}"
    env.setdefault("DOCKER_BUILDKIT", "0")
    env.setdefault("COMPOSE_BAKE", "false")
    env.setdefault("COMPOSE_PARALLEL_LIMIT", "1")
    if extra:
        env.update(extra)
    return env


def _pytest_env() -> dict[str, str]:
    return _pythonpath_env({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})


def _safe_clean(example_dir: Path, relative_paths: Iterable[str]) -> None:
    base = example_dir.resolve()
    for item in relative_paths:
        target = (example_dir / item).resolve()
        if target == base or base not in target.parents:
            raise ValueError(f"refusing to clean path outside example directory: {target}")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def _compile_example(
    example_id: str,
    example: dict[str, Any],
    artifact_dir: Path,
    *,
    clean: bool,
    name_prefix: str = "compile",
) -> dict[str, Any]:
    script = REPO_ROOT / example["script"]
    example_dir = script.parent
    if clean:
        _safe_clean(example_dir, example.get("clean", []))
    cmd = [sys.executable, script.name] + list(example.get("args", []))
    check = _run_command(
        f"{name_prefix}:{example_id}",
        cmd,
        artifact_dir,
        cwd=example_dir,
        env=_pythonpath_env(example.get("env", {})),
        timeout=int(example.get("timeout", 900)),
    )
    if check["status"] != "passed":
        return check

    missing = [item for item in example.get("expected", []) if not (example_dir / item).exists()]
    if missing:
        check["status"] = "failed"
        check["message"] = "expected compile outputs are missing"
        check["details"] = "Missing outputs: " + ", ".join(missing)
    return check


def run_static(artifact_dir: Path) -> int:
    manifest = load_manifest()
    checks: list[dict[str, Any]] = []

    errors = _validate_manifest(manifest)
    coverage = feature_coverage(manifest)
    _json_dump(artifact_dir / "feature-coverage.json", coverage)
    checks.append(
        {
            "name": "manifest",
            "status": "failed" if errors else "passed",
            "duration_s": 0.0,
            "message": "manifest validation failed" if errors else "manifest validation passed",
            "details": "\n".join(errors),
            "log_path": _rel(artifact_dir / "feature-coverage.json"),
        }
    )

    checks.append(_run_command("whitespace", _git_diff_check_command(), artifact_dir))

    compile_targets = [
        target
        for target in [
            "seedemu",
            "tests/control_plane",
            "tests/ci",
        ]
        if (REPO_ROOT / target).exists()
    ]
    example_dirs = sorted(
        {
            str(Path(manifest["examples"][example_id]["script"]).parent)
            for example_id in _example_ids(manifest, "compile")
        }
    )
    compile_targets.extend(example_dirs)
    checks.append(
        _run_command(
            "compileall",
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "-x",
                "seedemu/services/EthereumService/EthTemplates/",
            ]
            + compile_targets,
            artifact_dir,
        )
    )

    smoke = (
        "import seedemu; "
        "from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf; "
        "from seedemu.services import BgpLookingGlassService; "
        "from seedemu.compiler import Docker; "
        "import tests.ci.run_ci"
    )
    checks.append(_run_command("import-smoke", [sys.executable, "-c", smoke], artifact_dir, env=_pythonpath_env()))
    return _stage_result("static", checks, artifact_dir)


def run_unit(artifact_dir: Path) -> int:
    manifest = load_manifest()
    checks: list[dict[str, Any]] = []
    for group_id, group in manifest["unit_groups"].items():
        junit_path = artifact_dir / f"pytest-{_slug(group_id)}.xml"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={junit_path}",
        ] + list(group["pytest_args"])
        checks.append(_run_command(f"pytest:{group_id}", cmd, artifact_dir, env=_pytest_env(), timeout=900))
    return _stage_result("unit", checks, artifact_dir)


def run_example_compile(artifact_dir: Path) -> int:
    manifest = load_manifest()
    checks = [
        _compile_example(example_id, manifest["examples"][example_id], artifact_dir, clean=True)
        for example_id in _example_ids(manifest, "compile")
    ]
    return _stage_result("example-compile", checks, artifact_dir)


def run_example_build(artifact_dir: Path) -> int:
    manifest = load_manifest()
    checks: list[dict[str, Any]] = []
    for example_id in _example_ids(manifest, "build"):
        example = manifest["examples"][example_id]
        compile_check = _compile_example(
            example_id,
            example,
            artifact_dir,
            clean=True,
            name_prefix="compile-before-build",
        )
        checks.append(compile_check)
        if compile_check["status"] != "passed":
            continue

        script = REPO_ROOT / example["script"]
        compose_file = script.parent / "output" / "docker-compose.yml"
        checks.append(
            _run_command(
                f"docker-build:{example_id}",
                ["docker", "compose", "-f", str(compose_file), "build"],
                artifact_dir,
                env=_pythonpath_env(example.get("env", {})),
                timeout=int(example.get("build_timeout", 1800)),
            )
        )
    return _stage_result("example-build", checks, artifact_dir)


def run_runtime_integration(artifact_dir: Path) -> int:
    manifest = load_manifest()
    checks: list[dict[str, Any]] = []
    for group_id, group in manifest["runtime_groups"].items():
        junit_path = artifact_dir / f"pytest-{_slug(group_id)}.xml"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={junit_path}",
        ] + list(group["pytest_args"])
        checks.append(_run_command(f"runtime:{group_id}", cmd, artifact_dir, env=_pytest_env(), timeout=7200))
    return _stage_result("runtime-integration", checks, artifact_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run feature-oriented SEED Emulator CI stages.")
    parser.add_argument(
        "stage",
        choices=["static", "unit", "example-compile", "example-build", "runtime-integration"],
    )
    parser.add_argument("--artifact-dir", default="ci-artifacts", help="Directory for logs, JSON, and JUnit output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_dir = (REPO_ROOT / args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if args.stage == "static":
        return run_static(artifact_dir)
    if args.stage == "unit":
        return run_unit(artifact_dir)
    if args.stage == "example-compile":
        return run_example_compile(artifact_dir)
    if args.stage == "example-build":
        return run_example_build(artifact_dir)
    if args.stage == "runtime-integration":
        return run_runtime_integration(artifact_dir)
    raise AssertionError(f"unknown stage: {args.stage}")


if __name__ == "__main__":
    raise SystemExit(main())
