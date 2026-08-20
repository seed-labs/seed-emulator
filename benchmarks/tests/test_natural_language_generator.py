#!/usr/bin/env python3
"""Contracts, security, planning, approval and audit tests for generator.nl."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.nl.catalog import build_capability_catalog  # noqa: E402
from generator.nl.compiler import compile_intent  # noqa: E402
from generator.nl.models import BenchmarkIntent  # noqa: E402
from generator.nl.provider import (  # noqa: E402
    DeterministicLLMProvider, LLMProvider, MiMoProvider, OpenAICompatibleProvider,
)
from generator.nl.schema import BENCHMARK_INTENT_OUTPUT_SCHEMA, validate_provider_output  # noqa: E402
from generator.nl.security import inspect_natural_language  # noqa: E402
from generator.nl.session import (  # noqa: E402
    NaturalLanguageExecutor, NaturalLanguagePlanner, validate_blind_receipt,
)


FIXTURES = json.loads(
    (BENCHMARKS_DIR / "tests/fixtures/nl_benchmark_cases.json").read_text(encoding="utf-8")
)
READY_TEXT = FIXTURES["intent_cases"][0]["text"]


def expect_error(function, expected):
    try:
        function()
    except expected:
        return
    raise AssertionError(f"expected {expected.__name__}")


catalog = build_capability_catalog(BENCHMARKS_DIR)
assert {"nginx", "bind9", "postgresql", "network_observer"} <= set(catalog.application_ids)
assert {"network.netem", "container.stopped"} <= set(catalog.fault_ids)
assert "multi_agent_application_pilot" in catalog.topology_ids
assert len(catalog.fingerprint) == 64

provider = DeterministicLLMProvider()
messages = [{"role": "user", "content": READY_TEXT}]
first = provider.complete_structured(messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="stable-seed")
second = provider.complete_structured(messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="stable-seed")
assert first.output == second.output
validate_provider_output(first.output)
intent_a = BenchmarkIntent.from_provider_output(
    first.output, source_text=READY_TEXT, seed="stable-seed", provider_model="deterministic:v1"
)
intent_b = BenchmarkIntent.from_provider_output(
    second.output, source_text=READY_TEXT, seed="stable-seed", provider_model="deterministic:v1"
)
assert intent_a.to_dict() == intent_b.to_dict()
assert intent_a.fingerprint == intent_b.fingerprint
compiled = compile_intent(intent_a, catalog)
assert compiled.benchmark_request.execute_lifecycle is False
assert compiled.benchmark_request.publish is False
assert compiled.benchmark_request.topology_id == "multi_agent_application_pilot"
assert compiled.preview["mode"] == "plan_only_no_container_launch"
assert compiled.preview["execution_authorized"] is False

for attack_case in FIXTURES["structured_output_attacks"]:
    attack = dict(first.output)
    attack[attack_case["field"]] = attack_case["value"]
    expect_error(lambda attack=attack: validate_provider_output(attack), ValueError)
expect_error(lambda: BenchmarkIntent.from_dict({**intent_a.to_dict(), "extra": True}), ValueError)
for text in FIXTURES["prompt_injection_cases"]:
    assert not inspect_natural_language(text).allowed

validate_blind_receipt({
    "ai_invoked": False, "blind_mode": True,
    "passed": True, "topology_tainted": False,
})
for attack_case in FIXTURES["blind_receipt_attacks"]:
    receipt = {
        "ai_invoked": False, "blind_mode": True,
        "passed": True, "topology_tainted": False,
    }
    receipt[attack_case["field"]] = attack_case["value"]
    expect_error(lambda receipt=receipt: validate_blind_receipt(receipt), RuntimeError)


class MustNotRunProvider(LLMProvider):
    provider_id = "must_not_run"
    model_id = "must_not_run-v1"

    def complete_structured(self, messages, output_schema, *, seed):
        raise AssertionError("provider was invoked for blocked input")


class FailingProvider(LLMProvider):
    provider_id = "failing"
    model_id = "failing-v1"

    def complete_structured(self, messages, output_schema, *, seed):
        raise RuntimeError("synthetic provider outage")


with tempfile.TemporaryDirectory(prefix="nl-generator-tests-") as temporary:
    root = Path(temporary)
    planner = NaturalLanguagePlanner(BENCHMARKS_DIR, root)
    blocked = planner.plan(
        FIXTURES["prompt_injection_cases"][0],
        provider=MustNotRunProvider(), seed="blocked", session_id="blocked_case",
    )
    assert blocked["status"] == "blocked" and blocked["provider_invoked"] is False

    provider_error = planner.plan(
        READY_TEXT,
        provider=FailingProvider(), seed="provider-error", session_id="provider_error_case",
    )
    assert provider_error["status"] == "provider_error"
    assert provider_error["provider_invoked"] is True
    assert (root / "provider_error_case/provider_error.json").is_file()
    assert (root / "provider_error_case/audit.json").is_file()
    assert not (root / "provider_error_case/approval_challenge.json").exists()

    clarification = planner.plan(
        "生成 nginx 场景并注入容器停止故障",
        provider=provider, seed="clarify", session_id="clarification_case",
    )
    assert clarification["status"] == "needs_clarification"
    assert any(
        item["code"] == "missing_difficulty"
        for item in clarification["clarification"]["questions"]
    )

    extension = planner.plan(
        "生成 Redis 的 hard 场景并注入容器停止故障",
        provider=provider, seed="extension", session_id="extension_case",
    )
    assert extension["status"] == "extension_required"
    assert not (root / "extension_case/approval_challenge.json").exists()

    ready_first = planner.plan(
        READY_TEXT, provider=provider, seed="stable", session_id="ready_first"
    )
    ready_second = planner.plan(
        READY_TEXT, provider=provider, seed="stable", session_id="ready_second"
    )
    assert ready_first["status"] == ready_second["status"] == "ready"
    assert ready_first["intent_fingerprint"] == ready_second["intent_fingerprint"]
    assert ready_first["plan_fingerprint"] == ready_second["plan_fingerprint"]
    assert ready_second["provider_cache_hit"] is True
    assert ready_first["generator_plan"]["worker_count"] == 9
    assert ready_first["generator_plan"]["quality_passed"] is True
    assert ready_first["generator_plan"]["qualification_status"] == "not_requested"
    assert not list((root / "ready_first/bundle_plan").glob("lifecycle_round_*.json"))
    for name in (
        "input.json", "capability_snapshot.json", "provider_request.json",
        "provider_response.json", "normalized_intent.json", "preview.json",
        "approved_intent.json", "approval_challenge.json", "audit.json",
    ):
        assert (root / "ready_first" / name).is_file(), name
    challenge = json.loads((root / "ready_first/approval_challenge.json").read_text())
    assert ready_first["approval_token"] not in json.dumps(challenge)
    executor = NaturalLanguageExecutor(BENCHMARKS_DIR, root)
    expect_error(
        lambda: executor.execute(
            root / "ready_first/approved_intent.json", "incorrect-token"
        ),
        ValueError,
    )
    assert json.loads((root / "ready_first/approval_challenge.json").read_text())["consumed"] is False

missing_key = "NL_TEST_KEY_MUST_NOT_EXIST"
os.environ.pop(missing_key, None)
remote = OpenAICompatibleProvider(
    model_id="test-model", base_url="https://example.invalid/v1", api_key_env=missing_key
)
expect_error(
    lambda: remote.complete_structured(messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="x"),
    RuntimeError,
)


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return json.dumps({
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(first.output)},
            }],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
        }).encode("utf-8")


os.environ["MIMO_TEST_KEY"] = "temporary-test-value"
mimo = MiMoProvider(api_key_env="MIMO_TEST_KEY")
captured = {}


def fake_urlopen(request, timeout):
    captured["payload"] = json.loads(request.data.decode("utf-8"))
    captured["timeout"] = timeout
    return FakeHTTPResponse()


with patch("generator.nl.provider.urlopen", fake_urlopen):
    mimo_response = mimo.complete_structured(
        messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="mimo-test"
    )
os.environ.pop("MIMO_TEST_KEY")
validate_provider_output(mimo_response.output)
assert mimo_response.provider == "mimo"
assert captured["payload"]["response_format"] == {"type": "json_object"}
assert captured["payload"]["thinking"] == {"type": "disabled"}
assert captured["payload"]["max_completion_tokens"] == 4096
assert "seed" not in captured["payload"]
assert mimo_response.validation_attempts == 1
assert mimo_response.validation_failures == ()


class StructuredHTTPResponse(FakeHTTPResponse):
    def __init__(self, content, *, message_extra=None, finish_reason="stop"):
        self.content = content
        self.message_extra = message_extra or {}
        self.finish_reason = finish_reason

    def read(self, size=-1):
        message = {"content": self.content, **self.message_extra}
        return json.dumps({
            "choices": [{"finish_reason": self.finish_reason, "message": message}],
            "usage": {},
        }).encode("utf-8")


os.environ["MIMO_TEST_KEY"] = "temporary-test-value"
with patch(
    "generator.nl.provider.urlopen",
    lambda request, timeout: StructuredHTTPResponse(
        "\n  " + json.dumps(first.output) + "\r\n"
    ),
):
    whitespace_response = mimo.complete_structured(
        messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="legal-json-whitespace"
    )
assert whitespace_response.output == first.output
os.environ.pop("MIMO_TEST_KEY")


invalid_schema = {**first.output, "shell": "id"}
retry_responses = iter([
    StructuredHTTPResponse(json.dumps(invalid_schema)),
    StructuredHTTPResponse(json.dumps(first.output)),
])
retry_payloads = []


def retry_urlopen(request, timeout):
    retry_payloads.append(json.loads(request.data.decode("utf-8")))
    return next(retry_responses)


os.environ["MIMO_TEST_KEY"] = "temporary-test-value"
with patch("generator.nl.provider.urlopen", retry_urlopen):
    retried = mimo.complete_structured(
        messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="mimo-schema-retry"
    )
assert retried.validation_attempts == 2
assert len(retried.validation_failures) == 1
assert "local JSON Schema" in retried.validation_failures[0]
assert len(retry_payloads) == 2
assert "previous answer was rejected" in retry_payloads[1]["messages"][-1]["content"].lower()


strict_once = OpenAICompatibleProvider(
    model_id="test-model", base_url="https://example.invalid/v1",
    api_key_env="MIMO_TEST_KEY", response_format_mode="json_object",
    max_validation_attempts=1,
)
bad_contents = (
    '```json\n{"schema_version": 1}\n```',
    '{"schema_version":1,"schema_version":1}',
    '[{"schema_version":1}]',
    '{"schema_version":NaN}',
    '{"nested":' + '[' * 40 + '0' + ']' * 40 + '}',
    json.dumps(invalid_schema),
)
for bad_content in bad_contents:
    with patch(
        "generator.nl.provider.urlopen",
        lambda request, timeout, bad_content=bad_content: StructuredHTTPResponse(bad_content),
    ):
        expect_error(
            lambda: strict_once.complete_structured(
                messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="strict-json-attack"
            ),
            ValueError,
        )

with patch(
    "generator.nl.provider.urlopen",
    lambda request, timeout: StructuredHTTPResponse(
        json.dumps(first.output), message_extra={"tool_calls": [{"id": "escape"}]},
    ),
):
    expect_error(
        lambda: strict_once.complete_structured(
            messages, BENCHMARK_INTENT_OUTPUT_SCHEMA, seed="tool-call-attack"
        ),
        ValueError,
    )
os.environ.pop("MIMO_TEST_KEY")
assert "Return exactly one JSON object" in captured["payload"]["messages"][-1]["content"]

print("natural_language_generator_tests=passed")
