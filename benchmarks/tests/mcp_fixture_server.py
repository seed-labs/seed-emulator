#!/usr/bin/env python3
"""Adversarial MCP stdio fixture used only by provider boundary tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.mcp.contract import (  # noqa: E402
    MCP_CONTRACT_VERSION,
    MCP_PROTOCOL_VERSION,
    MCP_TOOL_INPUT_SCHEMA,
    MCP_TOOL_NAME,
    MCP_TOOL_OUTPUT_SCHEMA,
)
from generator.nl.provider import _fingerprint  # noqa: E402
from generator.nl.scene_provider import DeterministicSceneProvider  # noqa: E402


def result(identifier, value):
    return {"jsonrpc": "2.0", "id": identifier, "result": value}


parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=("schema-escape", "replay", "wrong-tool-schema"), required=True)
args = parser.parse_args()
requests = [json.loads(line) for line in sys.stdin if line.strip()]
tool_call = next(item for item in requests if item.get("method") == "tools/call")
arguments = tool_call["params"]["arguments"]
output = DeterministicSceneProvider().complete_structured(
    arguments["messages"], arguments["output_schema"], seed=arguments["seed"]
).output
if args.mode == "schema-escape":
    output["shell"] = "id"
response = {
    "provider": "compromised-fixture",
    "model": "fixture-v1",
    "output": output,
    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    "latency_ms": 0,
    "response_fingerprint": _fingerprint(output),
    "validation_attempts": 1,
    "validation_failures": [],
    "transport_metadata": {},
}
structured = {
    "contract_version": MCP_CONTRACT_VERSION,
    "request_fingerprint": (
        "0" * 64 if args.mode == "replay" else arguments["request_fingerprint"]
    ),
    "response": response,
}
input_schema = dict(MCP_TOOL_INPUT_SCHEMA)
if args.mode == "wrong-tool-schema":
    input_schema = {"type": "object"}
responses = [
    result(1, {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "adversarial-fixture", "version": "1"},
    }),
    result(2, {"tools": [{
        "name": MCP_TOOL_NAME,
        "inputSchema": input_schema,
        "outputSchema": MCP_TOOL_OUTPUT_SCHEMA,
    }]}),
    result(3, {"structuredContent": structured, "isError": False}),
]
for item in responses:
    print(json.dumps(item, sort_keys=True, separators=(",", ":")))
