"""Run embedded shell bodies for k8sTools Python entrypoints."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def runEmbeddedShell(script_path: Path, argv: list[str], shell_body: str) -> int:
    """Execute shell_body as the implementation of a Python entrypoint.

    Args:
        script_path: Path to the Python entrypoint being executed.
        argv: Arguments passed by the caller.
        shell_body: Embedded bash program.
    """
    entrypoint = script_path.resolve()
    env = os.environ.copy()
    env["SEED_K8S_ENTRYPOINT"] = str(entrypoint)
    completed = subprocess.run(["bash", "-c", shell_body, str(entrypoint), *argv], env=env)
    return int(completed.returncode)
