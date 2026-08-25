"""Small fail-closed MCP stdio client for the single provider Gateway tool."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterable, Mapping

from generator.mcp.contract import (
    MAX_MCP_MESSAGE_BYTES,
    MAX_MCP_STDERR_BYTES,
    MCP_PROTOCOL_VERSION,
    MCP_TOOL_INPUT_SCHEMA,
    MCP_TOOL_NAME,
    MCP_TOOL_OUTPUT_SCHEMA,
    canonical_sha256,
)
from generator.mcp.profile import MCPProfile
from generator.nl.provider import _strict_json_object


class MCPError(RuntimeError):
    """Base error for the MCP translation boundary."""


class MCPTransportError(MCPError):
    """A retry/fallback-eligible process or transport failure."""


class MCPProtocolError(MCPError):
    """A non-fallback protocol, contract, or untrusted-output failure."""


def _request(identifier: int, method: str, params: Mapping[str, Any] | None = None):
    value = {"jsonrpc": "2.0", "id": identifier, "method": method}
    if params is not None:
        value["params"] = dict(params)
    return value


def _encode(messages: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for item in messages
    )


class StdioMCPClient:
    def __init__(self, profile: MCPProfile, *, working_directory: Path):
        self.profile = profile
        self.working_directory = working_directory.resolve()

    def call_translation_tool(self, arguments: Mapping[str, Any]) -> Dict[str, Any]:
        payload = _encode([
            _request(1, "initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "benchmark-generator", "version": "1"},
            }),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            _request(2, "tools/list", {}),
            _request(3, "tools/call", {
                "name": MCP_TOOL_NAME,
                "arguments": dict(arguments),
            }),
        ])
        if len(payload) > MAX_MCP_MESSAGE_BYTES:
            raise MCPProtocolError("MCP request exceeds the message-size limit")
        try:
            process = subprocess.run(
                self.profile.command,
                input=payload,
                cwd=self.working_directory,
                env=os.environ.copy(),
                capture_output=True,
                timeout=self.profile.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MCPTransportError(
                f"MCP stdio transport failed for profile {self.profile.profile_id}: "
                f"{type(exc).__name__}"
            ) from exc
        if len(process.stdout) > MAX_MCP_MESSAGE_BYTES:
            raise MCPProtocolError("MCP response exceeds the message-size limit")
        if len(process.stderr) > MAX_MCP_STDERR_BYTES:
            raise MCPTransportError("MCP Gateway stderr exceeds the audit-size limit")
        if process.returncode != 0:
            raise MCPTransportError(
                f"MCP Gateway exited with status {process.returncode}"
            )
        responses: Dict[int, Dict[str, Any]] = {}
        try:
            for raw_line in process.stdout.splitlines():
                if not raw_line.strip():
                    continue
                value = _strict_json_object(raw_line)
                identifier = value.get("id")
                if identifier in responses:
                    raise ValueError("duplicate MCP JSON-RPC response id")
                if identifier is not None:
                    responses[identifier] = value
        except ValueError as exc:
            raise MCPProtocolError("MCP Gateway returned invalid JSON-RPC") from exc
        for identifier in (1, 2):
            if identifier not in responses:
                raise MCPProtocolError(f"MCP response {identifier} is missing")
            response = responses[identifier]
            if response.get("jsonrpc") != "2.0" or "error" in response:
                raise MCPProtocolError(f"MCP request {identifier} failed")
        if 3 not in responses:
            raise MCPProtocolError("MCP response 3 is missing")
        tool_response = responses[3]
        if tool_response.get("jsonrpc") != "2.0":
            raise MCPProtocolError("MCP tool response is not JSON-RPC 2.0")
        if "error" in tool_response:
            error = tool_response.get("error")
            data = error.get("data") if isinstance(error, Mapping) else None
            if isinstance(data, Mapping) and data.get("retryable") is True:
                raise MCPTransportError("MCP upstream provider reported a retryable failure")
            raise MCPProtocolError("MCP translation tool failed")
        initialized = responses[1].get("result")
        if not isinstance(initialized, Mapping):
            raise MCPProtocolError("MCP initialize result is malformed")
        if initialized.get("protocolVersion") != MCP_PROTOCOL_VERSION:
            raise MCPProtocolError("MCP protocol version was not negotiated")
        listing = responses[2].get("result")
        tools = listing.get("tools") if isinstance(listing, Mapping) else None
        if not isinstance(tools, list):
            raise MCPProtocolError("MCP tool listing is malformed")
        matching = [item for item in tools if isinstance(item, Mapping) and item.get("name") == MCP_TOOL_NAME]
        if len(matching) != 1:
            raise MCPProtocolError("trusted MCP translation tool is unavailable or ambiguous")
        if not isinstance(matching[0].get("inputSchema"), Mapping):
            raise MCPProtocolError("MCP translation tool has no input schema")
        if canonical_sha256(matching[0]["inputSchema"]) != canonical_sha256(MCP_TOOL_INPUT_SCHEMA):
            raise MCPProtocolError("MCP translation tool input schema does not match the contract")
        if canonical_sha256(matching[0].get("outputSchema", {})) != canonical_sha256(MCP_TOOL_OUTPUT_SCHEMA):
            raise MCPProtocolError("MCP translation tool output schema does not match the contract")
        result = tool_response.get("result")
        if not isinstance(result, Mapping) or result.get("isError") is True:
            raise MCPProtocolError("MCP translation tool reported an error")
        structured = result.get("structuredContent")
        if not isinstance(structured, Mapping):
            raise MCPProtocolError("MCP translation tool returned no structured content")
        return dict(structured)
