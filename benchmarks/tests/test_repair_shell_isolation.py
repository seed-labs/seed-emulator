"""Repair commands must not escape `docker exec` into the VM host shell."""

import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from scenarios.base import BaseScenario, has_unsafe_host_shell_syntax  # noqa: E402
from scenarios.strict_network_software import (  # noqa: E402
    StrictNetworkSoftwareScenario,
)


class _Base(BaseScenario):
    container = "target"

    def get_inject_cmd(self):
        return "docker exec target true"


class _Strict(StrictNetworkSoftwareScenario):
    container = "target"


unsafe_commands = (
    "docker exec target printf x > /etc/resolv.conf",
    "docker exec target true; echo pwned > /tmp/host-file",
    "docker exec target true && touch /tmp/host-file",
    "docker exec target cat /etc/resolv.conf | tee /tmp/host-file",
)
for command in unsafe_commands:
    assert has_unsafe_host_shell_syntax(command)
    assert not _Base().is_repair_command_allowed(command)
    assert not _Strict().is_repair_command_allowed(command)

safe_commands = (
    "docker exec target sed -i 's/old/new/' /tmp/config",
    "docker exec target sh -c 'printf x > /tmp/config && service app reload'",
)
for command in safe_commands:
    assert not has_unsafe_host_shell_syntax(command)
    assert _Base().is_repair_command_allowed(command)
    assert _Strict().is_repair_command_allowed(command)
