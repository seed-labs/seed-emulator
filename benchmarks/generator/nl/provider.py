"""Vendor-neutral structured LLM provider interface and safe implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Mapping, Sequence
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    output: Dict[str, Any]
    usage: Dict[str, int]
    latency_ms: int
    response_fingerprint: str

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
    ):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise ValueError("LLM base URL must be HTTP(S) without embedded credentials")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", api_key_env):
            raise ValueError("invalid API key environment variable name")
        if not 1 <= timeout_seconds <= 300:
            raise ValueError("LLM timeout is out of range")
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    def complete_structured(self, messages, output_schema, *, seed):
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing LLM API key environment: {self.api_key_env}")
        numeric_seed = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
        payload = {
            "model": self.model_id,
            "messages": list(messages),
            "temperature": 0,
            "seed": numeric_seed,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "benchmark_intent_v1",
                    "strict": True,
                    "schema": dict(output_schema),
                },
            },
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
        try:
            content = raw["choices"][0]["message"]["content"]
            output = content if isinstance(content, dict) else json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("LLM response does not contain structured JSON") from exc
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
        )
