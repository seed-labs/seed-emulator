from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


SUPPORTED_PLAYBOOK_VERSION = 1

SUPPORTED_ACTIONS = {
    "workspace_refresh",
    "inventory_list_nodes",
    "ops_exec",
    "ops_logs",
    "routing_bgp_summary",
    "sleep",
}


@dataclass(frozen=True)
class PlaybookStep:
    action: str
    step_id: str
    args: dict[str, Any]
    save_as: str | None


@dataclass(frozen=True)
class Playbook:
    version: int
    name: str
    defaults: dict[str, Any]
    steps: list[PlaybookStep]


def parse_playbook_yaml(playbook_yaml: str) -> Playbook:
    """Parse and validate a YAML playbook.

    YAML schema (v1):
      version: 1
      name: <str>
      defaults: { selector: {...}, timeout_seconds: 30, parallelism: 20, max_output_chars: 8000, ... }
      steps:
        - action: workspace_refresh|inventory_list_nodes|ops_exec|ops_logs|routing_bgp_summary|sleep
          id: <optional str>
          save_as: <optional str>
          ... action-specific args ...
    """
    data = yaml.safe_load(playbook_yaml) or {}
    if not isinstance(data, dict):
        raise ValueError("Playbook YAML must be a mapping (dict).")

    version = data.get("version", SUPPORTED_PLAYBOOK_VERSION)
    try:
        version_i = int(version)
    except Exception:
        raise ValueError("Playbook version must be an integer.") from None
    if version_i != SUPPORTED_PLAYBOOK_VERSION:
        raise ValueError(f"Unsupported playbook version: {version_i} (supported: {SUPPORTED_PLAYBOOK_VERSION})")

    name = str(data.get("name") or "playbook").strip() or "playbook"

    defaults = data.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError("playbook.defaults must be a dict.")

    steps_raw = data.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise ValueError("playbook.steps must be a non-empty list.")

    steps: list[PlaybookStep] = []
    for i, raw in enumerate(steps_raw, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"playbook.steps[{i}] must be a dict.")
        action = str(raw.get("action") or "").strip()
        if action not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported action in playbook.steps[{i}]: {action!r}")

        step_id = str(raw.get("id") or raw.get("name") or f"step{i}").strip() or f"step{i}"
        save_as = raw.get("save_as")
        save_as_s = str(save_as).strip() if save_as is not None and str(save_as).strip() else None

        args = {k: v for k, v in raw.items() if k not in {"action", "id", "name", "save_as"}}

        # Minimal per-action validation
        if action == "ops_exec":
            if "command" not in args:
                raise ValueError(f"playbook.steps[{i}] ops_exec requires 'command'.")
        if action in {"ops_exec", "ops_logs", "routing_bgp_summary", "inventory_list_nodes"}:
            sel = args.get("selector")
            if sel is not None and not isinstance(sel, dict):
                raise ValueError(f"playbook.steps[{i}] selector must be a dict.")
        if action == "sleep":
            if "seconds" not in args:
                raise ValueError(f"playbook.steps[{i}] sleep requires 'seconds'.")

        steps.append(PlaybookStep(action=action, step_id=step_id, args=args, save_as=save_as_s))

    return Playbook(version=version_i, name=name, defaults=defaults, steps=steps)

