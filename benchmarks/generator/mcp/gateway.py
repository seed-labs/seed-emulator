"""Single-purpose MCP stdio Gateway that wraps approved LLM provider adapters."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Mapping
from urllib.error import HTTPError, URLError

from generator.mcp.contract import (
    MAX_MCP_MESSAGE_BYTES,
    MCP_CONTRACT_VERSION,
    MCP_PROTOCOL_VERSION,
    MCP_TOOL_INPUT_SCHEMA,
    MCP_TOOL_NAME,
    MCP_TOOL_OUTPUT_SCHEMA,
    validate_contract,
)
from generator.nl.provider import MiMoProvider, OpenAICompatibleProvider, _strict_json_object
from generator.nl.scene_provider import DeterministicSceneProvider


def _provider(args):
    if args.vendor == "mimo":
        return MiMoProvider(
            model_id=args.model,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            timeout_seconds=args.timeout,
        )
    if args.vendor == "openai-compatible":
        return OpenAICompatibleProvider(
            model_id=args.model,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            timeout_seconds=args.timeout,
        )
    return DeterministicSceneProvider(args.model)


def _result(identifier, result):
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def _error(identifier, code: int, message: str, *, retryable: bool = False):
    value = {
        "jsonrpc": "2.0", "id": identifier,
        "error": {"code": code, "message": message[:512]},
    }
    if code == -32001:
        value["error"]["data"] = {"retryable": retryable}
    return value


def _retryable_provider_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code == 429 or 500 <= exc.code <= 599
    return isinstance(exc, (URLError, TimeoutError))


def _handle(request: Mapping[str, Any], provider):
    identifier = request.get("id")
    method = request.get("method")
    if method == "notifications/initialized":
        return None
    if request.get("jsonrpc") != "2.0" or not isinstance(identifier, int):
        return _error(identifier, -32600, "invalid JSON-RPC request")
    if method == "initialize":
        params = request.get("params")
        if not isinstance(params, Mapping) or params.get("protocolVersion") != MCP_PROTOCOL_VERSION:
            return _error(identifier, -32602, "unsupported MCP protocol version")
        return _result(identifier, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "benchmark-provider-gateway", "version": "1"},
        })
    if method == "tools/list":
        return _result(identifier, {"tools": [{
            "name": MCP_TOOL_NAME,
            "title": "Translate benchmark natural language",
            "description": "Return one schema-bound benchmark intent; never execute tools.",
            "inputSchema": MCP_TOOL_INPUT_SCHEMA,
            "outputSchema": MCP_TOOL_OUTPUT_SCHEMA,
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        }]})
    if method == "tools/call":
        params = request.get("params")
        if not isinstance(params, Mapping) or params.get("name") != MCP_TOOL_NAME:
            return _error(identifier, -32602, "unknown or invalid MCP tool")
        arguments = params.get("arguments")
        if not isinstance(arguments, Mapping):
            return _error(identifier, -32602, "MCP tool arguments must be an object")
        try:
            validate_contract(arguments, MCP_TOOL_INPUT_SCHEMA)
            response = provider.complete_structured(
                arguments["messages"], arguments["output_schema"], seed=arguments["seed"]
            )
            # Validate the same JSON-native representation that crosses stdio;
            # dataclass tuples (for validation failures) serialize as arrays.
            response_payload = json.loads(json.dumps(response.to_dict()))
            structured = {
                "contract_version": MCP_CONTRACT_VERSION,
                "request_fingerprint": arguments["request_fingerprint"],
                "response": response_payload,
            }
            # Gateway validates for diagnostics; Generator validates independently again.
            validate_contract(structured, MCP_TOOL_OUTPUT_SCHEMA)
            return _result(identifier, {
                "content": [{"type": "text", "text": "structured benchmark intent returned"}],
                "structuredContent": structured,
                "isError": False,
            })
        except Exception as exc:
            return _error(
                identifier, -32001,
                f"provider translation failed: {type(exc).__name__}",
                retryable=_retryable_provider_error(exc),
            )
    return _error(identifier, -32601, "method not found")


def build_parser():
    parser = argparse.ArgumentParser(description="Benchmark Provider MCP stdio Gateway")
    parser.add_argument(
        "--vendor", choices=("mimo", "openai-compatible", "deterministic-scene"),
        required=True,
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="https://invalid.local")
    parser.add_argument("--api-key-env", default="BENCHMARK_LLM_API_KEY")
    parser.add_argument("--timeout", type=int, default=120)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    provider = _provider(args)
    for line in sys.stdin.buffer:
        if len(line) > MAX_MCP_MESSAGE_BYTES:
            response = _error(None, -32700, "MCP message exceeds size limit")
        else:
            try:
                request = _strict_json_object(line)
                response = _handle(request, provider)
            except Exception:
                response = _error(None, -32700, "invalid JSON-RPC payload")
        if response is not None:
            encoded = json.dumps(response, sort_keys=True, separators=(",", ":")).encode("utf-8")
            sys.stdout.buffer.write(encoded + b"\n")
            sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
