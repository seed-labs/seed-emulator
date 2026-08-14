"""Cross-artifact safety and blind-isolation review."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Mapping


FORBIDDEN_COMMAND_MARKERS = (
    "docker rm", "docker kill", "docker compose", "docker-compose",
    "--privileged", "/var/run/docker.sock", "sudo ", "curl | sh",
    "wget | sh",
)
FORBIDDEN_HOST_SHELL = re.compile(r"(?:`|\$\(|\n|\r)")


def _walk(value: Any, path: str = ""):
    if isinstance(value, Mapping):
        for key, item in value.items():
            current = f"{path}.{key}" if path else str(key)
            yield current, key, item
            yield from _walk(item, current)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def review_bundle(
    *, public_bundle: Mapping[str, Any], private_bundle: Mapping[str, Any],
    forbidden_public_fields: Iterable[str], known_assets: Iterable[str],
) -> Dict[str, Any]:
    """Return an auditable report and fail closed on unsafe content."""
    errors, warnings = [], []
    forbidden = set(forbidden_public_fields)
    for path, key, value in _walk(public_bundle):
        if key in forbidden:
            errors.append(f"private field leaked into public bundle: {path}")
        if isinstance(value, str) and any(
            marker in value.lower() for marker in FORBIDDEN_COMMAND_MARKERS
        ):
            errors.append(f"unsafe command marker in public bundle: {path}")
    private_text = json.dumps(private_bundle, ensure_ascii=False).lower()
    for marker in FORBIDDEN_COMMAND_MARKERS:
        # Compiled, audited fault actions may legitimately use docker start;
        # destructive primitives remain forbidden everywhere.
        if marker in private_text:
            errors.append(f"forbidden mutation primitive in bundle: {marker}")
    for path, key, value in _walk(private_bundle):
        if key in {"command", "start_argv", "stop_argv"} and isinstance(value, str):
            if FORBIDDEN_HOST_SHELL.search(value):
                errors.append(f"unsafe shell syntax: {path}")
    assets = set(known_assets)
    if not assets:
        errors.append("bundle capability manifest has no assets")
    report = {
        "schema_version": 1,
        "approved": not errors,
        "errors": errors,
        "warnings": warnings,
        "asset_count": len(assets),
        "blind_metadata_isolated": not any(
            "leaked" in item for item in errors
        ),
    }
    if errors:
        raise ValueError("bundle safety review failed: " + "; ".join(errors))
    return report
