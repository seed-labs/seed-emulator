"""Generic OpenAI-compatible chat-completions provider for candidate agents."""

import json
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError


def _action_schema(allowed_actions: set[str]) -> dict[str, Any]:
    return {
        "name": "benchmark_candidate_action",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {"type": "string", "enum": sorted(allowed_actions)},
                "reasoning": {"type": "string", "minLength": 1},
            },
            "required": ["action", "reasoning"],
        },
    }


class _CandidateAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    reasoning: str = Field(min_length=1)


class OpenAICompatibleProvider:
    """Any OpenAI-compatible chat-completions endpoint as a candidate agent.

    The allowed action vocabulary is injected by the caller (from the scenario),
    so the provider itself contains no benchmark-specific action names. Replacing
    the vendor only requires a different endpoint, key, and model; the Adapter,
    grant, and scoring contract stay unchanged.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: int = 120,
        name: str = "openai-compatible",
        allowed_actions: set[str],
    ) -> None:
        if not allowed_actions:
            raise ValueError("allowed_actions must not be empty")
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._model = model
        self._timeout = timeout
        self.name = name
        self._allowed = allowed_actions

    def decide(
        self, messages: list[dict[str, str]]
    ) -> tuple[dict[str, str], dict[str, Any]]:
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": _action_schema(self._allowed),
            },
        }
        response = requests.post(
            f"{self._base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            action = _CandidateAction.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError("candidate returned an invalid action") from error
        if action.action not in self._allowed:
            raise ValueError("candidate selected an unapproved action")
        metadata = {
            "name": self.name,
            "model": payload.get("model", self._model),
            "usage": payload.get("usage", {}),
            "request_id": response.headers.get("x-request-id"),
        }
        return action.model_dump(), metadata
