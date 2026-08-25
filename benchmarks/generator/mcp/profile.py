"""Trusted MCP provider profiles; profiles contain names, never secret values."""

from __future__ import annotations

from dataclasses import dataclass
import re
import sys
from typing import Tuple
from urllib.parse import urlparse


PROFILE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")
ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


@dataclass(frozen=True)
class MCPProfile:
    profile_id: str
    vendor: str
    model_id: str
    command: Tuple[str, ...]
    timeout_seconds: int = 120
    transport: str = "stdio"
    endpoint: str | None = None
    credential_env: str | None = None

    def __post_init__(self) -> None:
        if not PROFILE_PATTERN.fullmatch(self.profile_id):
            raise ValueError("invalid MCP profile identity")
        if not PROFILE_PATTERN.fullmatch(self.vendor):
            raise ValueError("invalid MCP vendor identity")
        if not self.model_id or len(self.model_id) > 256:
            raise ValueError("invalid MCP model identity")
        if self.transport != "stdio":
            raise ValueError("only the isolated stdio MCP transport is supported")
        if not self.command or any(not isinstance(item, str) or not item for item in self.command):
            raise ValueError("MCP stdio command must be a non-empty argument tuple")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("MCP timeout is out of range")
        if self.endpoint is not None:
            parsed = urlparse(self.endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
                raise ValueError("invalid MCP profile upstream endpoint")
        if self.credential_env is not None and not ENV_PATTERN.fullmatch(self.credential_env):
            raise ValueError("invalid MCP profile credential environment name")

    def audit_dict(self):
        return {
            "profile_id": self.profile_id,
            "vendor": self.vendor,
            "model": self.model_id,
            "transport": self.transport,
            "timeout_seconds": self.timeout_seconds,
            "endpoint": self.endpoint,
            "credential_env": self.credential_env,
        }


def builtin_profile(
    profile_id: str,
    *,
    model_id: str | None = None,
    base_url: str | None = None,
    api_key_env: str | None = None,
    timeout_seconds: int = 120,
) -> MCPProfile:
    """Build a trusted in-repository Gateway command without a shell."""
    if profile_id == "mimo":
        model = model_id or "mimo-v2.5-pro"
        endpoint = base_url or "https://api.xiaomimimo.com/v1"
        key_env = api_key_env or "MIMO_API_KEY"
    elif profile_id == "openai-compatible":
        model = model_id or "gpt-4.1-mini"
        endpoint = base_url or "https://api.openai.com/v1"
        key_env = api_key_env or "BENCHMARK_LLM_API_KEY"
    elif profile_id == "deterministic-scene":
        model = model_id or "deterministic-scene-v2"
        endpoint = ""
        key_env = ""
    else:
        raise ValueError(f"unknown built-in MCP profile: {profile_id}")
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise ValueError("MCP Gateway upstream URL must be HTTP(S) without credentials")
    if key_env and not ENV_PATTERN.fullmatch(key_env):
        raise ValueError("invalid MCP Gateway credential environment name")
    command = [
        sys.executable, "-m", "generator.mcp.gateway",
        "--vendor", profile_id,
        "--model", model,
        "--timeout", str(timeout_seconds),
    ]
    if endpoint:
        command.extend(["--base-url", endpoint, "--api-key-env", key_env])
    return MCPProfile(
        profile_id=profile_id,
        vendor=profile_id,
        model_id=model,
        command=tuple(command),
        timeout_seconds=timeout_seconds,
        endpoint=endpoint or None,
        credential_env=key_env or None,
    )
