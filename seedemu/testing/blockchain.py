#!/usr/bin/env python3

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional

try:
    from .base import TestRunner
except ImportError:
    from base import TestRunner


class BlockchainTestRunner(TestRunner):
    """Runner for blockchain emulation tests."""

    runner_name = "blockchain"
    probe_handlers = {
        **TestRunner.probe_handlers,
        "json-rpc": "probe_json_rpc",
        "ethereum-rpc": "probe_json_rpc",
        "blockchain-rpc": "probe_json_rpc",
    }

    def probe_json_rpc(self, probe: Dict[str, Any]) -> tuple[bool, str]:
        payload = {
            "jsonrpc": "2.0",
            "id": probe.get("id", 1),
            "method": probe["method"],
            "params": probe.get("params", []),
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            str(probe["url"]),
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=int(probe.get("timeout", 10))) as response:
                text = response.read().decode("utf-8", errors="replace")
                if response.status != int(probe.get("expect_status", 200)):
                    return False, "HTTP {}, expected {}".format(response.status, probe.get("expect_status", 200))
                data = json.loads(text)
        except Exception as exc:
            return False, str(exc)

        if "expect_result" in probe and data.get("result") != probe["expect_result"]:
            return False, "JSON-RPC result did not match"
        if "expect_result_contains" in probe and str(probe["expect_result_contains"]) not in str(data.get("result")):
            return False, "JSON-RPC result did not contain expected text"
        if "expect_error" in probe and data.get("error") != probe["expect_error"]:
            return False, "JSON-RPC error did not match"
        if probe.get("expect_no_error", True) and data.get("error") is not None:
            return False, "JSON-RPC returned error {}".format(data.get("error"))
        return True, "JSON-RPC response matched"

    def required_probe_fields(self, probe_type: str) -> Optional[List[str]]:
        fields = {
            "json-rpc": ["url", "method"],
            "ethereum-rpc": ["url", "method"],
            "blockchain-rpc": ["url", "method"],
        }.get(probe_type)
        return fields if fields is not None else super().required_probe_fields(probe_type)
