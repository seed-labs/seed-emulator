#!/usr/bin/env python3
"""Enforce README_SYNC_REQUIRED coverage for benchmark maintenance layers."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path


BENCHMARKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS))
REQUIRED = (
    BENCHMARKS,
    BENCHMARKS / "agents",
    BENCHMARKS / "docs",
    BENCHMARKS / "generator",
    BENCHMARKS / "scenarios",
    BENCHMARKS / "specs",
    BENCHMARKS / "tests",
    BENCHMARKS / "topologies",
    BENCHMARKS / "topology_specs",
    BENCHMARKS / "reports",
)
MARKER = "README_SYNC_REQUIRED"
SYNC_SUFFIXES = {".py", ".json", ".sh"}
RUNTIME_LAYERS = {"reports"}
STDLIB_MODULES = {"compileall", "py_compile", "unittest"}


def git_paths(*args: str) -> set[Path]:
    result = subprocess.run(
        ["git", *args], cwd=BENCHMARKS, check=True, text=True,
        stdout=subprocess.PIPE,
    )
    paths = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = Path(line)
        # Git reports tracked paths relative to the repository root while
        # ls-files may report untracked paths relative to cwd. Normalize both.
        if path.parts and path.parts[0] == BENCHMARKS.name:
            path = Path(*path.parts[1:])
        paths.add(path)
    return paths


def changed_paths() -> set[Path]:
    tracked = git_paths("diff", "--name-only", "HEAD", "--", ".")
    untracked = git_paths("ls-files", "--others", "--exclude-standard", "--", ".")
    return tracked | untracked


def layer_for(path: Path) -> Path | None:
    parts = path.parts
    if not parts:
        return None
    if len(parts) == 1:
        return BENCHMARKS
    candidate = BENCHMARKS / parts[0]
    return candidate if candidate in REQUIRED else None


def main() -> None:
    errors: list[str] = []
    for directory in REQUIRED:
        readme = directory / "README.md"
        if not readme.is_file():
            errors.append(f"missing {readme.relative_to(BENCHMARKS)}")
        elif MARKER not in readme.read_text(encoding="utf-8"):
            errors.append(f"missing marker in {readme.relative_to(BENCHMARKS)}")

    changed = changed_paths()
    changed_readmes = {p for p in changed if p.name == "README.md"}
    for path in changed:
        if path.suffix not in SYNC_SUFFIXES or path.name == "README.md":
            continue
        layer = layer_for(path)
        if layer is None or layer.name in RUNTIME_LAYERS:
            continue
        expected = (layer / "README.md").relative_to(BENCHMARKS)
        if expected not in changed_readmes:
            errors.append(f"{path} changed without synchronized {expected}")

    if errors:
        raise SystemExit("README coverage failed:\n- " + "\n- ".join(sorted(errors)))
    print(f"README coverage passed: {len(REQUIRED)} benchmark layers")

    command_errors: list[str] = []
    for readme in sorted(BENCHMARKS.rglob("README.md")):
        if "meeting_reports" in readme.parts:
            continue
        content = readme.read_text(encoding="utf-8")
        for module in re.findall(r"python3\s+-m\s+([A-Za-z_]\w*(?:\.\w+)*)", content):
            if module not in STDLIB_MODULES and importlib.util.find_spec(module) is None:
                command_errors.append(
                    f"{readme.relative_to(BENCHMARKS)} references missing module {module}"
                )
        for script in re.findall(r"python3\s+([A-Za-z0-9_./-]+\.py)", content):
            if not (BENCHMARKS / script).is_file():
                command_errors.append(
                    f"{readme.relative_to(BENCHMARKS)} references missing script {script}"
                )
        for script in re.findall(r"\b(tests/[A-Za-z0-9_./-]+\.sh)\b", content):
            if not (BENCHMARKS / script).is_file():
                command_errors.append(
                    f"{readme.relative_to(BENCHMARKS)} references missing script {script}"
                )
        if "topologies/<entry>.py" in content:
            command_errors.append(
                f"{readme.relative_to(BENCHMARKS)} contains a non-runnable topology placeholder"
            )
        if re.search(r"python3\s+topologies/\S+\.py\s+--help", content):
            command_errors.append(
                f"{readme.relative_to(BENCHMARKS)} uses --help on an eager topology wrapper"
            )
    if command_errors:
        raise SystemExit("README command audit failed:\n- " + "\n- ".join(command_errors))
    print("README command audit passed")


if __name__ == "__main__":
    main()
