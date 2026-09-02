"""HTTP-only access to Agent Tool Service."""

from typing import Any

import requests


def invoke_tool(
    base_url: str,
    name: str,
    arguments: dict[str, Any],
    *,
    timeout: int = 300,
) -> dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/v1/tools/{name}/invoke",
        json=arguments,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "tool": name,
        "arguments": arguments,
        "result": payload["result"],
        "duration_ms": payload["duration_ms"],
    }


def wait_for_service(base_url: str, *, timeout: int = 30) -> dict[str, Any]:
    response = requests.get(f"{base_url.rstrip('/')}/api/v1/health", timeout=timeout)
    response.raise_for_status()
    return response.json()
