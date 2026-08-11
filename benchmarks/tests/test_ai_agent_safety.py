"""Safety and repair-protocol regression checks for the interactive AI agent."""

import json
import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR / "agents"))
sys.path.insert(0, str(BENCHMARKS_DIR))

from ai_agent import AIAgent  # noqa: E402


assert AIAgent.is_read_only_diagnostic_command("docker ps -a | grep exited")
assert AIAgent.is_read_only_diagnostic_command("docker logs stopped-host")
assert AIAgent.is_read_only_diagnostic_command(
    "docker logs stopped-host 2>&1 | tail -20"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router birdc show protocols"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router grep -E 'bgp|Name|peer' /etc/bird/bird.conf"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router ls -la /etc/bird"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router ps aux | grep bird"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router find /etc -name '*.conf'"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router traceroute -n 10.0.0.1"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router tc -s qdisc show dev net0"
)
assert AIAgent.is_read_only_diagnostic_command(
    "docker exec router sh -c 'named-checkconf /tmp/test.conf 2>&1'"
)
assert not AIAgent.is_read_only_diagnostic_command("docker start stopped-host")
assert not AIAgent.is_read_only_diagnostic_command(
    "docker exec router find /etc -name '*.conf' -delete"
)
assert not AIAgent.is_read_only_diagnostic_command(
    "docker ps | xargs docker stop"
)
assert not AIAgent.is_read_only_diagnostic_command(
    "docker exec router sed -i 's/999/2/' /etc/bird/bird.conf"
)
assert AIAgent.has_mutating_repair_command(["docker start stopped-host"])
assert not AIAgent.has_mutating_repair_command(["docker ps -a"])


agent = AIAgent(api_key="test", max_turns=2, verbose=False)
actually_run = []
agent.run_cmd = lambda command: actually_run.append(command) or "ok"
outputs = agent.execute_commands([
    "docker ps -a",
    "docker start stopped-host",
])
assert actually_run == ["docker ps -a"]
assert outputs["docker start stopped-host"].startswith("REJECTED:")
assert agent.diagnostic_commands_executed == ["docker ps -a"]
assert agent.diagnostic_commands_rejected == ["docker start stopped-host"]


# In repair mode, a final answer containing only observation commands must not
# terminate the conversation. The next answer contains an actual state change.
responses = iter([
    json.dumps({
        "action": "diagnose",
        "commands": [],
        "category": "service_not_running",
        "root_cause": "container exited",
        "symptoms": ["exited"],
        "proposed_fix": "start it",
        "confidence": 0.9,
        "repair_commands": ["docker ps -a"],
        "reasoning": "state delta",
        "target_container": ["stopped-host"],
        "artifact": "Docker container state",
        "faulty_value": "stopped",
        "expected_value": "running",
        "root_causes": [{
            "category": "container_not_running",
            "target_container": ["stopped-host"],
            "artifact": "Docker container state",
            "faulty_value": "stopped",
            "expected_value": "running",
        }],
    }),
    json.dumps({
        "action": "diagnose",
        "commands": [],
        "category": "service_not_running",
        "root_cause": "container exited",
        "symptoms": ["exited"],
        "proposed_fix": "start it",
        "confidence": 0.9,
        "repair_commands": ["docker start stopped-host"],
        "reasoning": "state delta",
        "target_container": ["stopped-host"],
        "artifact": "Docker container state",
        "faulty_value": "stopped",
        "expected_value": "running",
        "root_causes": [{
            "category": "container_not_running",
            "target_container": ["stopped-host"],
            "artifact": "Docker container state",
            "faulty_value": "stopped",
            "expected_value": "running",
        }],
    }),
])
agent = AIAgent(api_key="test", max_turns=2, verbose=False)
agent.call_ai_api = lambda _messages: next(responses)
empty_state = {"observations": {}}
diagnosis = agent.diagnose_interactive(
    repair_mode=True,
    baseline_state=empty_state,
    current_state=empty_state,
)
assert diagnosis.repair_commands == ["docker start stopped-host"]
assert len([turn for turn in agent.turns_log if turn.role == "assistant"]) == 2
