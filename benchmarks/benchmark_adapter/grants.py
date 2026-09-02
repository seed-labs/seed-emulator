"""Grant-spec loading and authoritative local policy checks."""

import json
from pathlib import Path
from typing import Any

_REQUIRED_KEYS = {
    "agent_view",
    "allowed_actions",
    "actions",
    "terminal_action",
    "target_service",
    "project",
    "max_calls",
    "benchmark_id",
    "tool_service_url",
    "trace_path",
}


class GrantSpecError(ValueError):
    """The grant spec file is missing, unreadable, or structurally invalid."""


def load_grant_spec(path: str | Path) -> dict[str, Any]:
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise GrantSpecError(f"unable to read grant spec: {error}") from error
    return validate_grant_spec(spec)


def validate_grant_spec(spec: dict[str, Any]) -> dict[str, Any]:
    missing = _REQUIRED_KEYS - spec.keys()
    if missing:
        raise GrantSpecError(f"grant spec missing keys: {sorted(missing)}")
    actions = spec["actions"]
    if not isinstance(actions, dict) or not actions:
        raise GrantSpecError("actions must be a non-empty object")
    terminal = spec["terminal_action"]
    if terminal not in actions:
        raise GrantSpecError("terminal_action must be one of the declared actions")
    for name, entry in actions.items():
        if not isinstance(entry, dict):
            raise GrantSpecError(f"action {name!r} must be an object")
        if name == terminal:
            if entry.get("tool"):
                raise GrantSpecError("terminal action must not declare a tool mapping")
            if not entry.get("terminal"):
                raise GrantSpecError("terminal_action must be marked terminal")
        elif not entry.get("tool"):
            raise GrantSpecError(f"action {name!r} requires a tool mapping")
    allowed = spec["allowed_actions"]
    if not allowed or set(allowed) != set(actions):
        raise GrantSpecError("allowed_actions must match the declared actions")
    if not isinstance(spec["max_calls"], int) or spec["max_calls"] < 1:
        raise GrantSpecError("max_calls must be a positive integer")
    return spec


def check_action(spec: dict[str, Any], action: str, calls_used: int) -> str | None:
    """Return a rejection reason, or None when the action is allowed."""

    if action not in spec["actions"]:
        return f"unknown action: {action}"
    if action not in spec["allowed_actions"]:
        return f"action not granted: {action}"
    if calls_used >= spec["max_calls"]:
        return "grant call budget exhausted"
    return None
