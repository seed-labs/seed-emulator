"""Candidate evaluation loop that runs entirely through the sandbox Adapter."""

import json
import time
from collections.abc import Callable
from typing import Any

import requests

ActionProvider = Callable[[list[dict[str, str]]], tuple[dict[str, str], dict[str, Any]]]

DEFAULT_SYSTEM_PROMPT = (
    "You are a candidate network repair agent. You have no Docker access. "
    "Return only the strict JSON action."
)


def wait_for_adapter(adapter_url: str, *, timeout: int = 60) -> None:
    """Poll the Adapter until it serves its agent view (it may still be booting)."""

    deadline = time.time() + timeout
    last_error: requests.RequestException | None = None
    while time.time() < deadline:
        try:
            response = requests.get(
                f"{adapter_url.rstrip('/')}/v1/agent_view", timeout=5
            )
            response.raise_for_status()
            return
        except requests.RequestException as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(f"adapter did not become ready: {last_error}")


def post_action(
    adapter_url: str, action: dict[str, str], *, timeout: int = 300
) -> dict[str, Any]:
    """Send one candidate action to the Adapter; normalize rejections and observations."""

    response = requests.post(
        f"{adapter_url.rstrip('/')}/v1/actions",
        json=action,
        timeout=timeout,
    )
    if response.status_code == 403:
        try:
            detail = response.json().get("detail", {})
        except ValueError:
            detail = {}
        return {
            "rejected": True,
            "code": detail.get("code", "grant_violation"),
            "message": detail.get("message", ""),
        }
    response.raise_for_status()
    payload = response.json()
    return payload.get("observation", payload)


def run_candidate_evaluation(
    adapter_url: str,
    provider: ActionProvider,
    agent_view: dict[str, Any],
    *,
    max_calls: int = 6,
    system_prompt: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Drive one candidate agent through the Adapter and return (trace, provider_metadata)."""

    messages = [
        {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(agent_view, ensure_ascii=False)},
    ]
    metadata: dict[str, Any] = {}
    trace: list[dict[str, Any]] = []
    for turn in range(max_calls):
        action, metadata = provider(messages)
        observation = post_action(adapter_url, action)
        trace.append({"turn": turn, **action, "observation": observation})
        messages.extend(
            [
                {"role": "assistant", "content": json.dumps(action)},
                {"role": "user", "content": json.dumps(observation)},
            ]
        )
        if action["action"] == "finish":
            break
    return trace, metadata
