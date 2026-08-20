"""Vendor-neutral structured LLM provider interface and safe implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Mapping, Sequence, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator


MAX_HTTP_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_STRUCTURED_CONTENT_BYTES = 512 * 1024
MAX_JSON_DEPTH = 32


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    output: Dict[str, Any]
    usage: Dict[str, int]
    latency_ms: int
    response_fingerprint: str
    validation_attempts: int = 1
    validation_failures: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LLMProvider(ABC):
    provider_id: str
    model_id: str

    @abstractmethod
    def complete_structured(
        self,
        messages: Sequence[Mapping[str, str]],
        output_schema: Mapping[str, Any],
        *,
        seed: str,
    ) -> ProviderResponse:
        """Return JSON data only; never execute or return tool calls."""


def _fingerprint(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"structured JSON contains duplicate key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str):
    raise ValueError(f"structured JSON contains invalid constant: {value}")


def _json_depth(value: Any) -> int:
    if isinstance(value, Mapping):
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def _strict_json_object(value: str | bytes) -> Dict[str, Any]:
    if isinstance(value, bytes):
        if len(value) > MAX_STRUCTURED_CONTENT_BYTES:
            raise ValueError("structured JSON exceeds the response-size limit")
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("structured JSON is not valid UTF-8") from exc
    elif isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_STRUCTURED_CONTENT_BYTES:
            raise ValueError("structured JSON exceeds the response-size limit")
        text = value
    else:
        raise ValueError("provider content must be a JSON string")
    candidate = text.strip()
    if not candidate:
        raise ValueError("provider content is empty")
    decoder = json.JSONDecoder(
        object_pairs_hook=_strict_pairs,
        parse_constant=_reject_json_constant,
    )
    try:
        output, end = decoder.raw_decode(candidate)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("provider content is not strict JSON") from exc
    if candidate[end:].strip():
        raise ValueError("provider content contains data outside the JSON object")
    if not isinstance(output, dict):
        raise ValueError("provider output must be exactly one JSON object")
    try:
        if _json_depth(output) > MAX_JSON_DEPTH:
            raise ValueError("provider JSON exceeds the nesting-depth limit")
    except RecursionError as exc:
        raise ValueError("provider JSON exceeds the nesting-depth limit") from exc
    return output


def _validate_structured_output(
    output: Mapping[str, Any], output_schema: Mapping[str, Any],
) -> None:
    errors = sorted(
        Draft202012Validator(output_schema).iter_errors(output),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        details = [
            {
                "path": "/".join(str(part) for part in error.absolute_path),
                "message": error.message,
            }
            for error in errors[:8]
        ]
        raise ValueError(f"provider output failed local JSON Schema: {details}")


class DeterministicLLMProvider(LLMProvider):
    """No-key provider for tests and demos; mimics constrained LLM output."""

    provider_id = "deterministic"

    def __init__(self, model_id: str = "deterministic-nl-v1"):
        self.model_id = model_id

    def complete_structured(self, messages, output_schema, *, seed):
        started = time.monotonic()
        text = next(
            (item["content"] for item in reversed(messages) if item.get("role") == "user"),
            "",
        )
        lowered = text.casefold()
        applications = []
        aliases = (
            ("nginx", ("nginx", "web server", "web服务")),
            ("bind9", ("bind9", "bind", "dns", "域名服务")),
            ("postgresql", ("postgresql", "postgres", "postgres 数据库")),
        )
        for application, names in aliases:
            if any(name in lowered for name in names):
                applications.append(application)

        faults = []
        fault_aliases = (
            ("network.netem", ("延迟", "丢包", "限速", "抖动", "latency", "packet loss", "jitter", "netem")),
            ("container.stopped", ("容器停止", "停止容器", "container stop", "stopped container")),
            ("dns.nameserver", ("nameserver", "dns 配置", "dns错误", "dns 故障")),
            ("network.acl.scoped", ("iptables", "acl", "防火墙规则")),
            ("routing.bird.wrong_asn", ("错误 asn", "wrong asn", "asn 配置")),
        )
        for fault_type, names in fault_aliases:
            if any(name in lowered for name in names):
                faults.append(fault_type)

        difficulty = next(
            (item for item in ("expert", "hard", "medium", "easy") if item in lowered),
            None,
        )
        scale_match = re.search(r"(?<!\d)(\d{1,5})\s*(?:个\s*)?(?:节点|nodes?|containers?)", lowered)
        assumptions = []
        if scale_match:
            scale = int(scale_match.group(1))
        else:
            scale = 5
            assumptions.append("scale_defaulted_to_5")
        count_match = re.search(r"(?<!\d)(\d{1,2})\s*(?:个\s*)?(?:故障|faults?)", lowered)
        fault_count = int(count_match.group(1)) if count_match else len(faults)
        relationship = "cascading" if any(x in lowered for x in ("级联", "cascading")) else (
            "independent" if fault_count > 1 or any(x in lowered for x in ("独立", "组合")) else "single"
        )
        topology_id = next(
            (
                item for item in (
                    "multi_agent_application_pilot", "small_ring", "scale_100",
                    "scale_500", "scale_1000", "scale_10000", "software_fault_demo",
                )
                if item in lowered
            ),
            None,
        )
        unknown = []
        for item in ("redis", "mysql", "apache", "kafka", "mongodb", "etcd"):
            if item in lowered:
                unknown.append(item)
        output = {
            "schema_version": 1,
            "objective": " ".join(text.split()),
            "applications": applications,
            "difficulty": difficulty,
            "scale": scale,
            "fault_types": faults,
            "fault_count": fault_count,
            "fault_relationship": relationship,
            "topology_id": topology_id,
            "observer_required": not any(x in lowered for x in ("不要观察节点", "without observer")),
            "publish_requested": any(x in lowered for x in ("正式发布", "publish", "release")),
            "unknown_requirements": unknown,
            "assumptions": assumptions,
        }
        return ProviderResponse(
            provider=self.provider_id,
            model=self.model_id,
            output=output,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            latency_ms=round((time.monotonic() - started) * 1000),
            response_fingerprint=_fingerprint(output),
        )


class OpenAICompatibleProvider(LLMProvider):
    """Minimal Chat Completions JSON-schema adapter; secrets remain in env."""

    provider_id = "openai_compatible"

    def __init__(
        self,
        *,
        model_id: str,
        base_url: str,
        api_key_env: str = "BENCHMARK_LLM_API_KEY",
        timeout_seconds: int = 60,
        response_format_mode: str = "json_schema",
        disable_thinking: bool = False,
        max_completion_tokens: int | None = None,
        send_seed: bool = True,
        max_validation_attempts: int = 2,
    ):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise ValueError("LLM base URL must be HTTP(S) without embedded credentials")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", api_key_env):
            raise ValueError("invalid API key environment variable name")
        if not 1 <= timeout_seconds <= 300:
            raise ValueError("LLM timeout is out of range")
        if response_format_mode not in {"json_schema", "json_object"}:
            raise ValueError("unsupported structured-output mode")
        if max_completion_tokens is not None and not 128 <= max_completion_tokens <= 131072:
            raise ValueError("LLM completion-token budget is out of range")
        if not 1 <= max_validation_attempts <= 3:
            raise ValueError("LLM validation-attempt limit is out of range")
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.response_format_mode = response_format_mode
        self.disable_thinking = disable_thinking
        self.max_completion_tokens = max_completion_tokens
        self.send_seed = send_seed
        self.max_validation_attempts = max_validation_attempts

    def complete_structured(self, messages, output_schema, *, seed):
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing LLM API key environment: {self.api_key_env}")
        numeric_seed = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
        request_messages = list(messages)
        if self.response_format_mode == "json_object":
            request_messages.append({
                "role": "system",
                "content": (
                    "Return exactly one JSON object matching this schema; do not add "
                    "Markdown or commentary: "
                    + json.dumps(output_schema, sort_keys=True, separators=(",", ":"))
                ),
            })
        response_format = (
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "benchmark_intent_v1",
                    "strict": True,
                    "schema": dict(output_schema),
                },
            }
            if self.response_format_mode == "json_schema"
            else {"type": "json_object"}
        )
        base_payload = {
            "model": self.model_id,
            "messages": request_messages,
            "temperature": 0,
            "response_format": response_format,
        }
        if self.send_seed:
            base_payload["seed"] = numeric_seed
        if self.disable_thinking:
            base_payload["thinking"] = {"type": "disabled"}
        if self.max_completion_tokens is not None:
            base_payload["max_completion_tokens"] = self.max_completion_tokens
        started = time.monotonic()
        failures = []
        raw = None
        output = None
        for attempt in range(1, self.max_validation_attempts + 1):
            payload = dict(base_payload)
            payload["messages"] = list(request_messages)
            if failures:
                payload["messages"].append({
                    "role": "system",
                    "content": (
                        "The previous answer was rejected by the local validator. "
                        "Return a complete JSON object matching "
                        "the original schema exactly. Do not add fields or commentary."
                    ),
                })
            request = Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
            if len(body) > MAX_HTTP_RESPONSE_BYTES:
                raise ValueError("LLM HTTP response exceeds the size limit")
            try:
                envelope = _strict_json_object(body)
                choices = envelope.get("choices")
                if not isinstance(choices, list) or not choices:
                    raise ValueError("LLM response has no choices")
                choice = choices[0]
                if not isinstance(choice, Mapping):
                    raise ValueError("LLM choice is malformed")
                if choice.get("finish_reason") not in (None, "stop"):
                    raise ValueError("LLM response is incomplete or filtered")
                message = choice.get("message")
                if not isinstance(message, Mapping):
                    raise ValueError("LLM response message is malformed")
                if message.get("tool_calls") or message.get("function_call"):
                    raise ValueError("LLM response attempted a tool call")
                if message.get("refusal"):
                    raise ValueError("LLM refused the structured-output request")
                output = _strict_json_object(message.get("content"))
                _validate_structured_output(output, output_schema)
                raw = envelope
                break
            except ValueError as exc:
                failures.append(str(exc))
                if attempt == self.max_validation_attempts:
                    raise ValueError(
                        "LLM failed strict structured-output validation after "
                        f"{attempt} attempts: {failures[-1]}"
                    ) from exc
        assert raw is not None and output is not None
        usage = raw.get("usage") or {}
        normalized_usage = {
            "input_tokens": int(usage.get("prompt_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }
        return ProviderResponse(
            provider=self.provider_id,
            model=self.model_id,
            output=dict(output),
            usage=normalized_usage,
            latency_ms=round((time.monotonic() - started) * 1000),
            response_fingerprint=_fingerprint(output),
            validation_attempts=len(failures) + 1,
            validation_failures=tuple(failures),
        )


class MiMoProvider(OpenAICompatibleProvider):
    """Xiaomi MiMo JSON-mode adapter with local strict-schema enforcement."""

    provider_id = "mimo"

    def __init__(
        self,
        *,
        model_id: str = "mimo-v2.5-pro",
        base_url: str = "https://api.xiaomimimo.com/v1",
        api_key_env: str = "MIMO_API_KEY",
        timeout_seconds: int = 120,
    ):
        super().__init__(
            model_id=model_id,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            response_format_mode="json_object",
            disable_thinking=True,
            max_completion_tokens=4096,
            send_seed=False,
        )
