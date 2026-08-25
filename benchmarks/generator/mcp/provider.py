"""LLMProvider implementation backed by one or more trusted MCP Gateways."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from generator.mcp.client import MCPTransportError, StdioMCPClient
from generator.mcp.contract import (
    MCP_CONTRACT_VERSION,
    MCP_TOOL_OUTPUT_SCHEMA,
    MCP_TOOL_SCHEMA_SHA256,
    canonical_sha256,
    validate_contract,
)
from generator.mcp.profile import MCPProfile
from generator.nl.provider import (
    LLMProvider,
    ProviderResponse,
    _fingerprint,
    _validate_structured_output,
)


class MCPProvider(LLMProvider):
    """Route structured translation through MCP and retain all local validation."""

    def __init__(
        self,
        primary: MCPProfile,
        *,
        working_directory: Path,
        fallbacks: Sequence[MCPProfile] = (),
    ):
        identities = [primary.profile_id, *(item.profile_id for item in fallbacks)]
        if len(identities) != len(set(identities)):
            raise ValueError("MCP provider profiles must be unique")
        self.profiles = (primary, *tuple(fallbacks))
        self.working_directory = working_directory.resolve()
        self.provider_id = "mcp_" + "_fallback_".join(identities)
        self.model_id = (
            "+".join(item.model_id for item in self.profiles)
            + f"@{MCP_TOOL_SCHEMA_SHA256[:12]}"
        )

    def audit_metadata(self):
        return {
            "transport": "mcp_stdio",
            "contract_version": MCP_CONTRACT_VERSION,
            "tool_schema_sha256": MCP_TOOL_SCHEMA_SHA256,
            "profiles": [item.audit_dict() for item in self.profiles],
            "fallback_policy": "transport_errors_only",
        }

    def complete_structured(
        self,
        messages: Sequence[Mapping[str, str]],
        output_schema: Mapping,
        *,
        seed: str,
    ) -> ProviderResponse:
        request = {
            "contract_version": MCP_CONTRACT_VERSION,
            "messages": [dict(item) for item in messages],
            "output_schema": dict(output_schema),
            "seed": seed,
        }
        request["request_fingerprint"] = canonical_sha256(request)
        transport_failures = []
        for profile in self.profiles:
            try:
                structured = StdioMCPClient(
                    profile, working_directory=self.working_directory
                ).call_translation_tool(request)
            except MCPTransportError as exc:
                transport_failures.append({
                    "profile": profile.profile_id,
                    "error_type": type(exc).__name__,
                })
                continue
            try:
                validate_contract(structured, MCP_TOOL_OUTPUT_SCHEMA)
                if structured["request_fingerprint"] != request["request_fingerprint"]:
                    raise ValueError("MCP response is not bound to this request")
                raw = structured["response"]
                output = raw["output"]
                _validate_structured_output(output, output_schema)
                if raw["response_fingerprint"] != _fingerprint(output):
                    raise ValueError("MCP provider response fingerprint mismatch")
                metadata = {
                    **self.audit_metadata(),
                    "selected_profile": profile.profile_id,
                    "selected_vendor": profile.vendor,
                    "upstream_provider": raw["provider"],
                    "transport_failures": transport_failures,
                }
                return ProviderResponse(
                    provider=f"mcp:{profile.profile_id}",
                    model=raw["model"],
                    output=dict(output),
                    usage=dict(raw["usage"]),
                    latency_ms=raw["latency_ms"],
                    response_fingerprint=raw["response_fingerprint"],
                    validation_attempts=raw["validation_attempts"],
                    validation_failures=tuple(raw["validation_failures"]),
                    transport_metadata=metadata,
                )
            except (KeyError, TypeError, ValueError) as exc:
                # Contract/schema failures are never fallback eligible.
                raise ValueError("MCP structured output failed local validation") from exc
        raise MCPTransportError(
            "all configured MCP provider transports failed: "
            + ",".join(item["profile"] for item in transport_failures)
        )
