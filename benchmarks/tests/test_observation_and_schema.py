"""Regression checks for attributed deltas, strict schema, and repair retries."""

import json
import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR / "agents"))
sys.path.insert(0, str(BENCHMARKS_DIR))

import ai_agent as ai_module  # noqa: E402
import observations as observations_module  # noqa: E402
from ai_agent import AIAgent, AIResponseError  # noqa: E402
from observations import (  # noqa: E402
    capture_network_state,
    diff_network_states,
    format_state_delta,
)
from scenarios.dns_failure import DnsFailureScenario  # noqa: E402


observations_source = (
    BENCHMARKS_DIR / "agents" / "observations.py"
).read_text(encoding="utf-8")
assert "iptables -S FORWARD" in observations_source
assert "iptables -S OUTPUT" in observations_source
assert "BIRD ASN and OSPF area summary" in observations_source
assert "Docker network attachments" in observations_source


source = {
    "command": "docker exec node cat /tmp/config",
    "container": "node",
    "artifact": "/tmp/config",
    "interface": "",
}
baseline = {
    "observations": {
        "config:node": {
            "id": "config:node",
            "kind": "config",
            "source": source,
            "output": "mode permit",
        },
        "unchanged": {
            "id": "unchanged",
            "kind": "noise",
            "source": source,
            "output": "same",
        },
    }
}
current = {
    "observations": {
        "config:node": {
            "id": "config:node",
            "kind": "config",
            "source": source,
            "output": "mode deny",
        },
        "unchanged": {
            "id": "unchanged",
            "kind": "noise",
            "source": source,
            "output": "same",
        },
    }
}
changes = diff_network_states(baseline, current)
assert [item["id"] for item in changes] == ["config:node"]
formatted = format_state_delta(baseline, current)
assert "docker exec node cat /tmp/config" in formatted
assert "container: `node`" in formatted
assert "artifact: `/tmp/config`" in formatted
assert "unchanged" not in formatted

large_commands = []
large_rows = "\n".join(f"bulk-host-{index}\trunning" for index in range(100))


def large_topology_run(command, timeout=8):
    large_commands.append((command, timeout))
    if command.startswith("docker ps -a"):
        return large_rows
    return "unexpected"


large_state = capture_network_state(run_command=large_topology_run)
assert large_state["capture_profile"] == "large_router_control_plane"
assert large_state["probe_count"] == 0
assert len(large_commands) == 1

large_router_commands = []
large_router_rows = "\n".join(
    ["as111brd-router0-10.111.0.254\trunning"]
    + [f"bulk-host-{index}\trunning" for index in range(99)]
)


def large_router_run(command, timeout=8):
    large_router_commands.append((command, timeout))
    if command.startswith("docker ps -a"):
        return large_router_rows
    if "birdc show protocols" in command:
        return "u_as24 BGP master4 up Established"
    if "bird.conf" in command:
        return "local 10.201.0.111 as 111;"
    if "docker inspect" in command:
        return '{"output_net_ix_ix201":{"IPAddress":"10.201.0.111"}}'
    if "iptables -S" in command:
        return "-P OUTPUT ACCEPT"
    return "unexpected"


large_router_state = capture_network_state(run_command=large_router_run)
assert large_router_state["capture_profile"] == "large_router_control_plane"
assert large_router_state["probe_count"] == 5
assert len(large_router_commands) == 6
large_router_kinds = {
    item["kind"]
    for key, item in large_router_state["observations"].items()
    if key.startswith(("bird:", "docker:", "firewall:"))
}
assert large_router_kinds == {
    "routing_protocols",
    "routing_config",
    "docker_networks",
    "firewall",
}

# Declarative captures must select probes from the compiled capability
# manifest, not infer all targets from scenario-specific container names.
declarative_commands = []
declarative_manifest = {
    "assets": [
        {"container": "decl-router", "role": "BorderRouter"},
        {"container": "decl-sensor", "role": "Host"},
        {"container": "decl-other-host", "role": "Host"},
    ],
    "fault_component_bindings": {"dns_nameserver": ["decl-sensor"]},
}


def declarative_run(command, timeout=8):
    declarative_commands.append((command, timeout))
    if command.startswith("docker ps -a"):
        return (
            "decl-router\trunning\n"
            "decl-sensor\trunning\n"
            "decl-other-host\trunning"
        )
    return "healthy probe output"


original_capability_lookup = observations_module._active_declarative_capabilities
try:
    observations_module._active_declarative_capabilities = (
        lambda _statuses: declarative_manifest
    )
    declarative_state = observations_module.capture_network_state(
        run_command=declarative_run
    )
finally:
    observations_module._active_declarative_capabilities = original_capability_lookup

assert declarative_state["capture_profile"] == "declarative_capability_driven"
declarative_probe_commands = [item[0] for item in declarative_commands[1:]]
assert any("decl-router" in command for command in declarative_probe_commands)
assert any(
    "decl-sensor" in command and "resolv.conf" in command
    for command in declarative_probe_commands
)
assert not any("decl-other-host" in command for command in declarative_probe_commands)
assert not any("route_reflector" in command for command in declarative_probe_commands)

small_commands = []


def small_topology_run(command, timeout=8):
    small_commands.append((command, timeout))
    if command.startswith("docker ps -a"):
        return (
            "as2brd-r101-10.101.0.2\trunning\n"
            "as150h-host_0-10.150.0.71\trunning"
        )
    return "healthy probe output"


small_state = capture_network_state(run_command=small_topology_run)
assert small_state["capture_profile"] == "full"
small_probe_commands = [item[0] for item in small_commands[1:]]
assert any(
    "docker inspect --format" in command
    and "as150h-host_0-10.150.0.71" in command
    for command in small_probe_commands
)
assert any("cat /etc/resolv.conf" in command for command in small_probe_commands)
assert any("bird.conf" in command for command in small_probe_commands)
assert any("birdc show ospf neighbors" in command for command in small_probe_commands)

dns_scenario = DnsFailureScenario()
full_score = dns_scenario.score_diagnosis(
    {
        "category": "dns_failure",
        "target_container": ["as150h-host_0-10.150.0.71"],
        "artifact": "/etc/resolv.conf",
        "faulty_value": dns_scenario.diagnosis_faulty_value,
        "expected_value": dns_scenario.diagnosis_expected_value,
    }
)
assert full_score["correct"] is True
wrong_target_score = dns_scenario.score_diagnosis(
    {
        "category": "dns_failure",
        "target_container": ["wrong-host"],
        "artifact": "/etc/resolv.conf",
        "faulty_value": dns_scenario.diagnosis_faulty_value,
        "expected_value": dns_scenario.diagnosis_expected_value,
    }
)
assert wrong_target_score["components"]["category"] is True
assert wrong_target_score["correct"] is False


def diagnosis_payload(command: str) -> str:
    return json.dumps(
        {
            "action": "diagnose",
            "commands": [],
            "reasoning": "baseline delta identifies node",
            "category": "test_fault",
            "root_cause": "mode is deny",
            "symptoms": ["config changed"],
            "proposed_fix": "restore permit",
            "confidence": 0.95,
            "repair_commands": [command],
            "target_container": ["node"],
            "artifact": "/tmp/config",
            "faulty_value": "mode deny",
            "expected_value": "mode permit",
            "root_causes": [
                {
                    "category": "test_fault",
                    "target_container": ["node"],
                    "artifact": "/tmp/config",
                    "faulty_value": "mode deny",
                    "expected_value": "mode permit",
                }
            ],
        }
    )


# Rejected/failed repairs are fed back into the same conversation and retried.
responses = iter(
    (
        diagnosis_payload("docker exec wrong sed -i 's/deny/permit/' /tmp/config"),
        diagnosis_payload("docker exec node sed -i 's/deny/permit/' /tmp/config"),
    )
)
seen_messages = []
agent = AIAgent(api_key="test", max_turns=2, verbose=False)
agent.call_ai_api = lambda messages: (
    seen_messages.append(list(messages)) or next(responses)
)
attempts = []


def attempt_handler(diagnosis):
    attempts.append(diagnosis.repair_commands[0])
    if len(attempts) == 1:
        return {
            "verified": False,
            "rejections": [
                {
                    "command": attempts[-1],
                    "reason": "target outside mutation scope",
                }
            ],
            "executions": [],
            "verification_output": "",
        }
    return {
        "verified": True,
        "rejections": [],
        "executions": [{"command": attempts[-1], "output": ""}],
        "verification_output": "healthy",
    }


diagnosis = agent.diagnose_interactive(
    repair_mode=True,
    baseline_state=baseline,
    current_state=current,
    repair_attempt_handler=attempt_handler,
)
assert diagnosis.target_container == ["node"]
assert len(attempts) == 2
assert "target outside mutation scope" in json.dumps(
    seen_messages[1], ensure_ascii=False
)


class _Response:
    def __init__(self, finish_reason="stop"):
        self.finish_reason = finish_reason

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "finish_reason": self.finish_reason,
                    "message": {"content": diagnosis_payload("docker start node")},
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 2,
                "total_tokens": 3,
            },
        }


captured_request = {}
original_post = ai_module.requests.post
try:
    ai_module.requests.post = lambda *args, **kwargs: (
        captured_request.update(kwargs.get("json", {})) or _Response()
    )
    api_agent = AIAgent(api_key="test", verbose=False)
    api_agent.call_ai_api([{"role": "user", "content": "test"}])
    response_format = captured_request["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert "target_container" in response_format["json_schema"]["schema"]["required"]
    assert "root_causes" in response_format["json_schema"]["schema"]["required"]

    invalid_transport = api_agent.parse_response("```json\n{")
    assert invalid_transport.error
    captured_request.clear()
    api_agent.call_ai_api([{"role": "user", "content": "retry"}])
    assert "response_format" not in captured_request

    ai_module.requests.post = lambda *args, **kwargs: _Response("length")
    truncated_agent = AIAgent(api_key="test", verbose=False)
    try:
        truncated_agent.call_ai_api([{"role": "user", "content": "test"}])
        raise AssertionError("truncated response was accepted")
    except AIResponseError:
        pass
finally:
    ai_module.requests.post = original_post

# OpenAI-compatible providers sometimes concatenate two JSON values despite
# response_format=json_schema. The first complete object is isolated and still
# subjected to the full local schema validation.
concatenated_agent = AIAgent(api_key="test", verbose=False)
first_payload = diagnosis_payload("docker start node")
concatenated = concatenated_agent.parse_response(
    first_payload + "\n" + first_payload
)
assert concatenated.category == "test_fault"
assert concatenated.repair_commands == ["docker start node"]

# MIMO can emit literal newlines inside an otherwise complete JSON string.
# The transport quirk is normalized, while the full local schema remains
# mandatory after decoding.
literal_newline = first_payload.replace(
    "baseline delta identifies node",
    "baseline delta\nidentifies node",
)
normalized = concatenated_agent.parse_response(literal_newline)
assert normalized.category == "test_fault"
assert normalized.repair_commands == ["docker start node"]

# The provider sometimes returns an action-specific object followed by the
# beginning of another object. A complete minimal diagnostic request remains
# safe because it still passes the read-only command gate before execution.
minimal_request = concatenated_agent.parse_response(
    '{"action":"execute_commands","commands":["docker ps -a"]}\n{"'
)
assert minimal_request.commands == ["docker ps -a"]
assert minimal_request.reasoning

# A duplicated opening brace is treated as malformed transport framing; the
# first complete actionable object is isolated without guessing any fields.
double_brace_request = concatenated_agent.parse_response(
    '{{"action":"execute_commands","commands":["docker ps -a"]}'
)
assert double_brace_request.commands == ["docker ps -a"]

single_command_request = concatenated_agent.parse_response(
    '{"action":"execute_commands","commands":"docker ps -a"}'
)
assert single_command_request.commands == ["docker ps -a"]

# A large max_turns value must not create a tight retry storm while DNS/API
# connectivity is down.
outage_agent = AIAgent(api_key="test", max_turns=1000, verbose=False)
outage_calls = []


def unavailable_api(_messages):
    outage_calls.append(1)
    raise AIResponseError("temporary DNS failure", retryable=True)


original_sleep = ai_module.time.sleep
try:
    ai_module.time.sleep = lambda _seconds: None
    outage_agent.call_ai_api = unavailable_api
    outage_result = outage_agent.diagnose_interactive(
        baseline_state={"observations": {}},
        current_state={"observations": {}},
    )
finally:
    ai_module.time.sleep = original_sleep

assert len(outage_calls) == 3
assert outage_result.category == "unknown"
assert "API 熔断" in outage_result.root_cause
