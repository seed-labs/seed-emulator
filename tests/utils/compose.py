"""Utilities for resolving the available Docker Compose command.

Some environments provide the V2 subcommand `docker compose`, while others
still ship the standalone `docker-compose` binary.  Tests that rely on
Compose should use the helper below to stay compatible across both setups.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import List, Tuple


def detect_compose_command() -> Tuple[List[str], int]:
    """Return the Compose invocation and detected major version.

    Returns
    -------
    (command, version)
        * command: list, e.g. ["docker", "compose"] or ["docker-compose"].
        * version: integer 1 or 2 for logging/compatibility decisions.

    Raises
    ------
    RuntimeError
        If neither Compose variant is available on the host.
    """

    candidates = [
        (["docker", "compose"], ["docker", "compose", "version"], 2),
        (["docker-compose"], ["docker-compose", "version"], 1),
    ]
    for cmd, check_cmd, version in candidates:
        if shutil.which(cmd[0]) is None:
            continue
        if cmd[0] == "docker" and shutil.which("docker") is None:
            continue
        result = subprocess.run(check_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return cmd, version
    raise RuntimeError("Neither 'docker compose' nor 'docker-compose' is available on this system")
