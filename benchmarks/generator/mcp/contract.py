"""Versioned MCP tool contract shared by clients and provider gateways."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from jsonschema import Draft202012Validator


MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_CONTRACT_VERSION = "benchmark-scene-mcp-v1"
MCP_TOOL_NAME = "translate_benchmark_scene"
MAX_MCP_MESSAGE_BYTES = 2 * 1024 * 1024
MAX_MCP_STDERR_BYTES = 64 * 1024

MCP_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "contract_version", "messages", "output_schema", "seed",
        "request_fingerprint",
    ],
    "properties": {
        "contract_version": {"const": MCP_CONTRACT_VERSION},
        "messages": {
            "type": "array", "minItems": 1, "maxItems": 16,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["role", "content"],
                "properties": {
                    "role": {"enum": ["system", "user", "assistant"]},
                    "content": {"type": "string", "maxLength": 262144},
                },
            },
        },
        "output_schema": {"type": "object"},
        "seed": {"type": "string", "minLength": 1, "maxLength": 256},
        "request_fingerprint": {
            "type": "string", "pattern": "^[0-9a-f]{64}$",
        },
    },
}

MCP_TOOL_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["contract_version", "request_fingerprint", "response"],
    "properties": {
        "contract_version": {"const": MCP_CONTRACT_VERSION},
        "request_fingerprint": {
            "type": "string", "pattern": "^[0-9a-f]{64}$",
        },
        "response": {
            "type": "object", "additionalProperties": False,
            "required": [
                "provider", "model", "output", "usage", "latency_ms",
                "response_fingerprint", "validation_attempts",
                "validation_failures",
            ],
            "properties": {
                "provider": {"type": "string", "minLength": 1, "maxLength": 128},
                "model": {"type": "string", "minLength": 1, "maxLength": 256},
                "output": {"type": "object"},
                "usage": {
                    "type": "object", "additionalProperties": False,
                    "required": ["input_tokens", "output_tokens", "total_tokens"],
                    "properties": {
                        "input_tokens": {"type": "integer", "minimum": 0},
                        "output_tokens": {"type": "integer", "minimum": 0},
                        "total_tokens": {"type": "integer", "minimum": 0},
                    },
                },
                "latency_ms": {"type": "integer", "minimum": 0},
                "response_fingerprint": {
                    "type": "string", "pattern": "^[0-9a-f]{64}$",
                },
                "validation_attempts": {"type": "integer", "minimum": 1, "maximum": 3},
                "validation_failures": {
                    "type": "array", "maxItems": 3,
                    "items": {"type": "string", "maxLength": 1024},
                },
                "transport_metadata": {"type": "object"},
            },
        },
    },
}


def canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_contract(value: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            {
                "path": "/".join(str(part) for part in error.absolute_path),
                "message": error.message,
            }
            for error in errors[:8]
        ]
        raise ValueError(f"MCP contract validation failed: {details}")


MCP_TOOL_SCHEMA_SHA256 = canonical_sha256({
    "input": MCP_TOOL_INPUT_SCHEMA,
    "output": MCP_TOOL_OUTPUT_SCHEMA,
})
