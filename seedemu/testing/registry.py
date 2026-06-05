#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from .base import TestRunner, TestRunnerError
    from .blockchain import BlockchainTestRunner
    from .internet import InternetTestRunner
    from .satellite import SatelliteTestRunner
except ImportError:
    from base import TestRunner, TestRunnerError
    from blockchain import BlockchainTestRunner
    from internet import InternetTestRunner
    from satellite import SatelliteTestRunner


RUNNER_REGISTRY = {
    "generic": TestRunner,
    "test": TestRunner,
    "internet": InternetTestRunner,
    "satellite": SatelliteTestRunner,
    "blockchain": BlockchainTestRunner,
}


def create_runner(
    manifest_path: Path,
    artifact_dir: Optional[Path] = None,
    runner: Optional[str] = None,
) -> TestRunner:
    """Create a runner from an explicit name or the manifest's runner field."""

    runner_name = runner
    if runner_name is None:
        runner_name = read_runner_name(manifest_path)
    runner_cls = RUNNER_REGISTRY.get(str(runner_name))
    if runner_cls is None:
        raise TestRunnerError("unknown runner: {}".format(runner_name))
    return runner_cls(manifest_path, artifact_dir=artifact_dir)


def read_runner_name(manifest_path: Path) -> str:
    try:
        import yaml
    except ImportError:
        return "generic"

    path = manifest_path.resolve()
    if not path.is_file():
        return "generic"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return str(data.get("runner", "generic"))
    return "generic"
