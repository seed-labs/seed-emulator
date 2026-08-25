#!/usr/bin/env python3
"""Enforce README coverage and code/documentation synchronization."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Iterable, Set


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCHMARKS_DIR.parent
GENERATOR_DIR = BENCHMARKS_DIR / "generator"
MARKER = "README_SYNC_REQUIRED"
SOURCE_SUFFIXES = {".py", ".json"}


def source_directories() -> Set[Path]:
    directories = set()
    for path in GENERATOR_DIR.rglob("*"):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in SOURCE_SUFFIXES
        ):
            directories.add(path.parent)
    return directories


def validate_readme_coverage() -> None:
    missing = []
    invalid = []
    for directory in sorted(source_directories()):
        readme = directory / "README.md"
        if not readme.is_file():
            missing.append(str(readme.relative_to(BENCHMARKS_DIR)))
            continue
        if MARKER not in readme.read_text(encoding="utf-8"):
            invalid.append(str(readme.relative_to(BENCHMARKS_DIR)))
    agents = GENERATOR_DIR / "AGENTS.md"
    if MARKER not in agents.read_text(encoding="utf-8"):
        invalid.append("generator/AGENTS.md")
    if missing or invalid:
        raise AssertionError(
            f"generator README coverage failed: missing={missing}, marker_missing={invalid}"
        )


def validate_readme_inventory() -> None:
    """Require each README to name every maintained source/data file it owns."""
    undocumented = []
    for directory in sorted(source_directories()):
        content = (directory / "README.md").read_text(encoding="utf-8")
        for source in sorted(directory.iterdir()):
            if (
                not source.is_file()
                or source.suffix not in SOURCE_SUFFIXES
                or source.name == "__init__.py"
            ):
                continue
            if source.name not in content:
                undocumented.append({
                    "source": str(source.relative_to(BENCHMARKS_DIR)),
                    "readme": str((directory / "README.md").relative_to(BENCHMARKS_DIR)),
                })
    if undocumented:
        raise AssertionError(f"generator README inventory is stale: {undocumented}")


def git_paths(arguments: Iterable[str]) -> Set[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def changed_paths() -> Set[str]:
    paths = git_paths(
        ["diff", "--name-only", "HEAD", "--", "benchmarks/generator"]
    )
    paths.update(
        git_paths(
            [
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                "benchmarks/generator",
            ]
        )
    )
    base = os.environ.get("GENERATOR_README_DIFF_BASE", "").strip()
    if base:
        paths.update(
            git_paths(
                [
                    "diff",
                    "--name-only",
                    f"{base}...HEAD",
                    "--",
                    "benchmarks/generator",
                ]
            )
        )
    return paths


def required_readmes(source: Path) -> Set[str]:
    """Return the source directory README and every ancestor through generator/."""
    directory = source.parent
    required = set()
    generator = Path("benchmarks/generator")
    while directory == generator or generator in directory.parents:
        required.add((directory / "README.md").as_posix())
        if directory == generator:
            break
        directory = directory.parent
    return required


def validate_changed_directories() -> None:
    paths = changed_paths()
    changed_readmes = {
        path for path in paths if Path(path).name.casefold() == "readme.md"
    }
    missing_updates = []
    for path in sorted(paths):
        candidate = Path(path)
        if candidate.suffix not in SOURCE_SUFFIXES or "__pycache__" in candidate.parts:
            continue
        for required in sorted(required_readmes(candidate)):
            if required not in changed_readmes:
                missing_updates.append({"source": path, "required": required})
    if missing_updates:
        raise AssertionError(
            "generator code/data changed without cascading README updates: "
            f"{missing_updates}"
        )


def validate_cascade_contract() -> None:
    expected = {
        "benchmarks/generator/bundle/examples/boundary_validation/README.md",
        "benchmarks/generator/bundle/examples/README.md",
        "benchmarks/generator/bundle/README.md",
        "benchmarks/generator/README.md",
    }
    actual = required_readmes(Path(
        "benchmarks/generator/bundle/examples/boundary_validation/example.json"
    ))
    if actual != expected:
        raise AssertionError(f"generator README cascade contract drifted: {sorted(actual)}")


def main() -> int:
    validate_readme_coverage()
    validate_readme_inventory()
    validate_cascade_contract()
    validate_changed_directories()
    directories = sorted(
        str(path.relative_to(BENCHMARKS_DIR)) for path in source_directories()
    )
    print(f"generator_readme_coverage=passed directories={len(directories)}")
    for directory in directories:
        print(f"covered={directory}/README.md")
    print("generator_readme_cascade_sync=passed")
    print("generator_readme_inventory=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
