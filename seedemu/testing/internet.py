#!/usr/bin/env python3

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    from .base import TestRunner
except ImportError:
    from base import TestRunner


class InternetTestRunner(TestRunner):
    """Runner for Internet-style SEED Emulator tests."""

    runner_name = "internet"
    probe_handlers = {
        **TestRunner.probe_handlers,
        "ping": "probe_ping",
        "dns": "probe_dns",
        "bgp-route": "probe_bgp_route",
        "mpls-config": "probe_mpls_config",
    }

    def probe_ping(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        command = "ping -c {} {}".format(int(probe.get("count", 3)), probe["target"])
        exec_probe = dict(probe)
        exec_probe["type"] = "exec"
        exec_probe["command"] = command
        exec_probe.setdefault("expect_exit", 0)
        return self.probe_exec(exec_probe)

    def probe_dns(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        query = str(probe["query"])
        record_type = str(probe.get("record_type", "A"))
        command = (
            "getent hosts {}".format(query)
            if record_type in {"A", "AAAA"}
            else "nslookup -type={} {}".format(record_type, query)
        )
        if probe.get("server"):
            command = "nslookup -type={} {} {}".format(record_type, query, probe["server"])

        if probe.get("service"):
            exec_probe = dict(probe)
            exec_probe["type"] = "exec"
            exec_probe["command"] = command
            exec_probe.setdefault("expect_exit", 0)
            return self.probe_exec(exec_probe)

        result = self.run_command(
            "probe-{}".format(self.slug(probe["name"])),
            ["sh", "-lc", command],
            cwd=self.emulation_dir,
            timeout=int(probe.get("timeout", 30)),
        )
        if result.returncode != 0:
            return False, "DNS command exited {}".format(result.returncode)
        return self.check_text_expectations(probe, result.stdout or "", result.stderr or "")

    def probe_bgp_route(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        command = str(probe.get("command", "birdc show route {}".format(probe["prefix"])))
        exec_probe = dict(probe)
        exec_probe["type"] = "exec"
        exec_probe["command"] = command
        exec_probe.setdefault("expect_exit", 0)
        return self.probe_exec(exec_probe)

    def probe_mpls_config(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        interfaces = [str(item) for item in probe.get("interfaces", [])]
        checks = ["test -s /mpls_ifaces.txt", "grep -q 'mpls ldp' /etc/frr/frr.conf"]
        checks.extend("grep -q '^{}$' /mpls_ifaces.txt".format(re.escape(interface)) for interface in interfaces)
        exec_probe = dict(probe)
        exec_probe["type"] = "exec"
        exec_probe["command"] = " && ".join(checks)
        exec_probe.setdefault("expect_exit", 0)
        return self.probe_exec(exec_probe)

    def required_probe_fields(self, probe_type: str) -> Optional[List[str]]:
        fields = {
            "ping": ["service", "target"],
            "dns": ["query"],
            "bgp-route": ["service", "prefix"],
            "mpls-config": ["service"],
        }.get(probe_type)
        return fields if fields is not None else super().required_probe_fields(probe_type)
