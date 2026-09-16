#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
from typing import List


def docker_compose_command() -> List[str]:
    docker = shutil.which("docker")
    if docker is not None:
        result = subprocess.run(
            [docker, "compose", "version"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return [docker, "compose"]

    docker_compose = shutil.which("docker-compose")
    if docker_compose is not None:
        return [docker_compose]

    return ["docker", "compose"]
