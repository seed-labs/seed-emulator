"""JSON Schema boundary for structured natural-language model output."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from jsonschema import Draft202012Validator


BENCHMARK_INTENT_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "BenchmarkIntentProviderOutputV1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "objective", "applications", "difficulty", "scale",
        "fault_types", "fault_count", "fault_relationship", "topology_id",
        "observer_required", "publish_requested", "unknown_requirements",
        "assumptions",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "objective": {"type": "string", "minLength": 1, "maxLength": 2000},
        "applications": {
            "type": "array", "maxItems": 16, "uniqueItems": True,
            "items": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,95}$"},
        },
        "difficulty": {
            "oneOf": [
                {"type": "null"},
                {"enum": ["easy", "medium", "hard", "expert"]},
            ]
        },
        "scale": {"type": "integer", "minimum": 1, "maximum": 10000},
        "fault_types": {
            "type": "array", "maxItems": 64, "uniqueItems": True,
            "items": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,95}$"},
        },
        "fault_count": {"type": "integer", "minimum": 0, "maximum": 64},
        "fault_relationship": {"enum": ["single", "independent", "cascading"]},
        "topology_id": {
            "oneOf": [
                {"type": "null"},
                {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{2,95}$"},
            ]
        },
        "observer_required": {"type": "boolean"},
        "publish_requested": {"type": "boolean"},
        "unknown_requirements": {
            "type": "array", "maxItems": 32, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
        },
        "assumptions": {
            "type": "array", "maxItems": 32, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 512},
        },
    },
}


def validate_provider_output(value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(BENCHMARK_INTENT_OUTPUT_SCHEMA).iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            {"path": "/".join(str(part) for part in error.absolute_path), "message": error.message}
            for error in errors
        ]
        raise ValueError(f"LLM structured output failed JSON Schema: {details}")
