"""Tests for the provider-agnostic candidate interface (design principle 12)."""

import json
import unittest
from typing import ClassVar
from unittest.mock import patch

from benchmark_agent.providers.openai_compat import OpenAICompatibleProvider

_ALLOWED = {"inspect_dns", "probe_dns", "repair_dns", "finish"}


def _response(content: str):
    class FakeResponse:
        headers: ClassVar[dict[str, str]] = {"x-request-id": "req-1"}

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "model": "fake-model",
                "choices": [{"message": {"content": content}}],
                "usage": {"total_tokens": 5},
            }

    return FakeResponse()


class OpenAICompatibleProviderTests(unittest.TestCase):
    def _provider(self) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            "http://fake/v1", "key", "fake-model", allowed_actions=_ALLOWED
        )

    def test_valid_action(self) -> None:
        content = json.dumps({"action": "repair_dns", "reasoning": "fix it"})
        with patch(
            "benchmark_agent.providers.openai_compat.requests.post",
            return_value=_response(content),
        ) as post:
            action, metadata = self._provider().decide(
                [{"role": "user", "content": "x"}]
            )
        self.assertEqual(action, {"action": "repair_dns", "reasoning": "fix it"})
        self.assertEqual(metadata["name"], "openai-compatible")
        self.assertEqual(metadata["model"], "fake-model")
        post.assert_called_once()
        body = post.call_args.kwargs["json"]
        schema = body["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            schema["properties"]["action"]["enum"], sorted(_ALLOWED)
        )

    def test_invalid_json_rejected(self) -> None:
        with patch(
            "benchmark_agent.providers.openai_compat.requests.post",
            return_value=_response("not json"),
        ), self.assertRaises(ValueError):
            self._provider().decide([{"role": "user", "content": "x"}])

    def test_unapproved_action_rejected(self) -> None:
        content = json.dumps({"action": "rm_all", "reasoning": "x"})
        with patch(
            "benchmark_agent.providers.openai_compat.requests.post",
            return_value=_response(content),
        ), self.assertRaises(ValueError):
            self._provider().decide([{"role": "user", "content": "x"}])

    def test_empty_allowed_actions_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OpenAICompatibleProvider(
                "http://fake/v1", "key", "fake-model", allowed_actions=set()
            )


if __name__ == "__main__":
    unittest.main()
