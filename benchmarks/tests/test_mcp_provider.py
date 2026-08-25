#!/usr/bin/env python3
"""Contract, routing, audit, and scene integration tests for MCP providers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.mcp.client import MCPProtocolError  # noqa: E402
from generator.mcp.contract import (  # noqa: E402
    MCP_CONTRACT_VERSION,
    MCP_TOOL_NAME,
    MCP_TOOL_SCHEMA_SHA256,
)
from generator.mcp.profile import MCPProfile, builtin_profile  # noqa: E402
from generator.mcp.provider import MCPProvider  # noqa: E402
from generator.nl.catalog import build_capability_catalog  # noqa: E402
from generator.nl.scene_models import BENCHMARK_SCENE_OUTPUT_SCHEMA  # noqa: E402
from generator.nl.scene_provider import build_scene_messages  # noqa: E402
from generator.nl.scene_session import NaturalLanguageScenePlanner  # noqa: E402


TEXT = (
    "生成一个包含3个AS、每个AS 2台主机的全连接拓扑，部署nginx和网络观测，"
    "设置网络延迟故障，难度hard"
)
catalog = build_capability_catalog(BENCHMARKS_DIR)
messages = build_scene_messages(TEXT, catalog.snapshot)
deterministic = builtin_profile("deterministic-scene", timeout_seconds=30)

provider = MCPProvider(deterministic, working_directory=BENCHMARKS_DIR)
response = provider.complete_structured(
    messages, BENCHMARK_SCENE_OUTPUT_SCHEMA, seed="mcp-contract-test"
)
assert response.provider == "mcp:deterministic-scene"
assert response.output["topology"]["as_count"] == 3
assert response.output["topology"]["hosts_per_as"] == 2
assert response.output["topology"]["edge_policy"] == "mesh"
assert response.transport_metadata["contract_version"] == MCP_CONTRACT_VERSION
assert response.transport_metadata["tool_schema_sha256"] == MCP_TOOL_SCHEMA_SHA256
assert response.transport_metadata["selected_profile"] == "deterministic-scene"
assert response.transport_metadata["fallback_policy"] == "transport_errors_only"
assert "command" not in json.dumps(response.transport_metadata)

# Process failures are fallback eligible, and the selected profile is audited.
failed = MCPProfile(
    profile_id="unavailable",
    vendor="unavailable",
    model_id="unavailable-v1",
    command=(sys.executable, "-c", "import sys;sys.exit(7)"),
    timeout_seconds=10,
)
fallback_provider = MCPProvider(
    failed,
    working_directory=BENCHMARKS_DIR,
    fallbacks=(deterministic,),
)
fallback_response = fallback_provider.complete_structured(
    messages, BENCHMARK_SCENE_OUTPUT_SCHEMA, seed="mcp-fallback-test"
)
assert fallback_response.transport_metadata["selected_profile"] == "deterministic-scene"
assert fallback_response.transport_metadata["transport_failures"] == [{
    "profile": "unavailable", "error_type": "MCPTransportError",
}]


def adversarial_profile(mode):
    return MCPProfile(
        profile_id=f"fixture-{mode}",
        vendor="fixture",
        model_id="fixture-v1",
        command=(
            sys.executable, str(BENCHMARKS_DIR / "tests/mcp_fixture_server.py"),
            "--mode", mode,
        ),
        timeout_seconds=10,
    )


# A compromised Gateway cannot smuggle executable fields, replay another request,
# or advertise a weakened Tool schema. None of these failures may use fallback.
for mode, expected in (
    ("schema-escape", ValueError),
    ("replay", ValueError),
    ("wrong-tool-schema", MCPProtocolError),
):
    attacked = MCPProvider(
        adversarial_profile(mode),
        working_directory=BENCHMARKS_DIR,
        fallbacks=(deterministic,),
    )
    try:
        attacked.complete_structured(
            messages, BENCHMARK_SCENE_OUTPUT_SCHEMA, seed=f"mcp-{mode}"
        )
    except expected:
        pass
    else:
        raise AssertionError(f"MCP adversarial mode was accepted: {mode}")

# Malformed/untrusted protocol output is not fallback eligible.
malformed = MCPProfile(
    profile_id="malformed",
    vendor="malformed",
    model_id="malformed-v1",
    command=(sys.executable, "-c", "print('{}')"),
    timeout_seconds=10,
)
non_bypass = MCPProvider(
    malformed,
    working_directory=BENCHMARKS_DIR,
    fallbacks=(deterministic,),
)
try:
    non_bypass.complete_structured(
        messages, BENCHMARK_SCENE_OUTPUT_SCHEMA, seed="mcp-no-schema-bypass"
    )
except MCPProtocolError:
    pass
else:
    raise AssertionError("MCP protocol rejection incorrectly used a fallback")

try:
    MCPProfile(
        profile_id="remote",
        vendor="remote",
        model_id="remote-v1",
        command=("remote",),
        transport="streamable_http",
    )
except ValueError:
    pass
else:
    raise AssertionError("unimplemented remote MCP transport was accepted")

# The real scene planner consumes the MCP provider without invoking topology/Docker.
with tempfile.TemporaryDirectory(prefix="mcp-scene-test-") as temporary:
    sessions = Path(temporary) / "sessions"
    planner = NaturalLanguageScenePlanner(BENCHMARKS_DIR, sessions)
    with patch(
        "generator.nl.scene_session.compile_topology",
        side_effect=AssertionError("MCP plan-only invoked topology compilation"),
    ):
        planned = planner.plan(
            TEXT,
            provider=provider,
            seed="mcp-planner-test",
            session_id="mcp_scene_plan",
        )
    assert planned["status"] == "ready"
    session = Path(planned["session"])
    request = json.loads((session / "provider_request.json").read_text(encoding="utf-8"))
    stored = json.loads((session / "provider_response.json").read_text(encoding="utf-8"))
    assert request["provider_transport"]["contract_version"] == MCP_CONTRACT_VERSION
    assert stored["transport_metadata"]["selected_profile"] == "deterministic-scene"
    assert planned["preview"]["mode"] == "plan_only_no_docker_state_change"
    assert not (session / "scene_delivery").exists()

assert MCP_TOOL_NAME == "translate_benchmark_scene"
print("MCP provider gateway tests: PASS")
