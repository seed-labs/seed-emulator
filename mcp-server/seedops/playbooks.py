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

SUPPORTED_ON_ERROR = {"stop", "continue"}


@dataclass(frozen=True)
class PlaybookStep:
    action: str
    step_id: str
    args: dict[str, Any]
    save_as: str | None
    retries: int | None
    retry_delay_seconds: float | None
    on_error: str | None


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
      defaults:
        selector: {...}
        timeout_seconds: 30
        parallelism: 20
        max_output_chars: 8000
        on_error: stop|continue
        retries: 0
        retry_delay_seconds: 1
      steps:
        - action: workspace_refresh|inventory_list_nodes|ops_exec|ops_logs|routing_bgp_summary|sleep
          id: <optional str>
          save_as: <optional str>
          on_error: <optional stop|continue>
          retries: <optional int>
          retry_delay_seconds: <optional number>
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
    if "on_error" in defaults:
        on_err = str(defaults.get("on_error") or "").strip()
        if on_err not in SUPPORTED_ON_ERROR:
            raise ValueError("playbook.defaults.on_error must be 'stop' or 'continue'.")
    if "retries" in defaults:
        try:
            retries_i = int(defaults.get("retries"))
        except Exception:
            raise ValueError("playbook.defaults.retries must be an int.") from None
        if retries_i < 0:
            raise ValueError("playbook.defaults.retries must be >= 0.")
    if "retry_delay_seconds" in defaults:
        try:
            delay_f = float(defaults.get("retry_delay_seconds"))
        except Exception:
            raise ValueError("playbook.defaults.retry_delay_seconds must be a number.") from None
        if delay_f < 0:
            raise ValueError("playbook.defaults.retry_delay_seconds must be >= 0.")

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

        step_on_error = raw.get("on_error")
        on_error_s = str(step_on_error).strip() if step_on_error is not None and str(step_on_error).strip() else None
        if on_error_s is not None and on_error_s not in SUPPORTED_ON_ERROR:
            raise ValueError(f"playbook.steps[{i}].on_error must be 'stop' or 'continue'.")

        retries_raw = raw.get("retries")
        retries_i: int | None = None
        if retries_raw is not None:
            try:
                retries_i = int(retries_raw)
            except Exception:
                raise ValueError(f"playbook.steps[{i}].retries must be an int.") from None
            if retries_i < 0:
                raise ValueError(f"playbook.steps[{i}].retries must be >= 0.")

        delay_raw = raw.get("retry_delay_seconds")
        delay_f: float | None = None
        if delay_raw is not None:
            try:
                delay_f = float(delay_raw)
            except Exception:
                raise ValueError(f"playbook.steps[{i}].retry_delay_seconds must be a number.") from None
            if delay_f < 0:
                raise ValueError(f"playbook.steps[{i}].retry_delay_seconds must be >= 0.")

        args = {
            k: v
            for k, v in raw.items()
            if k not in {"action", "id", "name", "save_as", "on_error", "retries", "retry_delay_seconds"}
        }

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

        steps.append(
            PlaybookStep(
                action=action,
                step_id=step_id,
                args=args,
                save_as=save_as_s,
                retries=retries_i,
                retry_delay_seconds=delay_f,
                on_error=on_error_s,
            )
        )

    return Playbook(version=version_i, name=name, defaults=defaults, steps=steps)
