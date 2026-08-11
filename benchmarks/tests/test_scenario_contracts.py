"""Static and mocked contracts for every benchmark scenario."""

import os
import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))
sys.path.insert(0, str(BENCHMARKS_DIR / "agents"))

import scenarios.base as base_module  # noqa: E402
import benchmark_cli as cli_module  # noqa: E402
from scenarios import (  # noqa: E402
    MAIN_SCENARIOS,
    SCENARIO_CATALOG,
    get_scenarios_by_track,
)
from scenarios.base import BaseScenario  # noqa: E402
from scenarios.dns_failure import DnsFailureScenario  # noqa: E402
from scenarios.dual_fault_bgp_ospf import (  # noqa: E402
    DualFaultBgpOspfScenario,
)
from scenarios.dual_fault_dns_network import (  # noqa: E402
    DualFaultDnsNetworkScenario,
)
from scenarios.missing_bgp_peering import (  # noqa: E402
    MissingBgpPeeringScenario,
)
from scenarios.netem_packet_loss import NetemPacketLossScenario  # noqa: E402
from scenarios.wireguard_allowed_ips import (  # noqa: E402
    WireGuardAllowedIpsScenario,
)
from scenarios.wrong_docker_network import (  # noqa: E402
    WrongDockerNetworkScenario,
)


VALID_TRACKS = {
    "network_functional",
    "network_control_plane",
    "config_lint",
    "advanced",
    "robustness",
}

names = [scenario_class.name for scenario_class in SCENARIO_CATALOG]
assert len(names) == len(set(names))
assert set(MAIN_SCENARIOS).issubset(set(SCENARIO_CATALOG))
assert get_scenarios_by_track("main") == MAIN_SCENARIOS
assert get_scenarios_by_track("all") == SCENARIO_CATALOG

for scenario_class in SCENARIO_CATALOG:
    scenario = scenario_class()
    assert scenario.benchmark_track in VALID_TRACKS
    assert scenario.difficulty in {"basic", "core", "advanced"}
    assert isinstance(scenario.scenario_seed, int)
    assert scenario.get_inject_cmd().strip()
    assert scenario.get_verify_cmd().strip()
    assert scenario.get_fix_cmd().strip()
    # Empty/error output must never be accepted as a healthy state.
    assert scenario.check_verified("") is False
    if scenario.main_score_eligible:
        assert scenario.benchmark_track not in {
            "config_lint",
            "advanced",
            "robustness",
        }

for scenario_class in get_scenarios_by_track("config_lint"):
    assert scenario_class.main_score_eligible is False

dns = DnsFailureScenario()
assert "127.0.0.11" in dns.get_fix_cmd()
assert "10.153.0.73" not in dns.get_fix_cmd()
assert "getent hosts" in dns.get_verify_cmd()

missing_bgp = MissingBgpPeeringScenario()
assert "birdc disable u_as2" in missing_bgp.get_inject_cmd()
assert "# FAULT" not in missing_bgp.get_inject_cmd()
assert missing_bgp.check_verified("u_as2 BGP down") is False
assert missing_bgp.check_verified("BGP_PEERING_OK") is True

wrong_network = WrongDockerNetworkScenario()
assert "docker network disconnect" in wrong_network.get_inject_cmd()
assert "ip link set" not in wrong_network.get_inject_cmd()
assert "ping" in wrong_network.get_verify_cmd()

for dual in (DualFaultBgpOspfScenario(), DualFaultDnsNetworkScenario()):
    assert dual.fault_type == "multiple_faults"
    assert len(dual.expected_root_causes) == 2
    assert dual.main_score_eligible is False
    assert dual.benchmark_track == "advanced"

# Multi-root matching is order-independent and requires the right count.
dual = DualFaultBgpOspfScenario()
predicted_roots = [
    {
        key: value
        for key, value in root.items()
        if not key.endswith("_aliases")
    }
    for root in reversed(dual._expected_root_cause_specs())
]
dual_score = dual.score_diagnosis(
    {
        "category": "multiple_faults",
        "target_container": [dual.container],
        "artifact": dual.diagnosis_artifact,
        "faulty_value": dual.diagnosis_faulty_value,
        "expected_value": dual.diagnosis_expected_value,
        "root_causes": predicted_roots,
    }
)
assert dual_score["correct"] is True
assert dual_score["root_count_correct"] is True

# Semantic matching accepts detailed live qdisc output and artifact aliases.
netem = NetemPacketLossScenario()
netem_score = netem.score_diagnosis(
    {
        "category": netem.fault_type,
        "target_container": [netem.target],
        "artifact": "root qdisc on net0",
        "faulty_value": (
            "qdisc netem 8008: dev net0 root refcnt 9 "
            "limit 1000 loss 100%"
        ),
        "expected_value": "qdisc noqueue 0: dev net0 root refcnt 2",
    }
)
assert netem_score["components"]["faulty_value"] is True
assert netem_score["components"]["expected_value"] is True

wireguard = WireGuardAllowedIpsScenario()
wireguard_score = wireguard.score_diagnosis(
    {
        "category": wireguard.fault_type,
        "target_container": [wireguard.left],
        "artifact": "WireGuard peer allowed ips configuration",
        "faulty_value": wireguard.diagnosis_faulty_value,
        "expected_value": wireguard.diagnosis_expected_value,
    }
)
assert wireguard_score["components"]["artifact"] is True

observations_source = (
    BENCHMARKS_DIR / "agents" / "observations.py"
).read_text(encoding="utf-8")
assert "cat /tmp/benchmark_frr.conf" not in observations_source
assert "cat /tmp/benchmark_bird.conf" not in observations_source


class _LifecycleScenario(BaseScenario):
    name = "contract_lifecycle"
    topology = "test"
    fault_type = "test_fault"
    diagnosis_artifact = "state"
    diagnosis_faulty_value = "bad"
    diagnosis_expected_value = "good"
    state = "unknown"

    def get_fix_cmd(self):
        return "fix"

    def get_inject_cmd(self):
        return "inject"

    def get_verify_cmd(self):
        return "verify"

    def check_verified(self, output):
        return output == "good"


scenario = _LifecycleScenario()
original_run = base_module.run
original_run_with_status = base_module.run_with_status
try:
    def fake_run(command, timeout=180):
        if command == "fix":
            scenario.state = "good"
            return ""
        if command == "verify":
            return scenario.state
        return ""

    def fake_run_with_status(command, timeout=180):
        if command == "inject":
            scenario.state = "bad"
            return 0, ""
        if command == "fix":
            scenario.state = "good"
            return 0, ""
        return 1, "unexpected"

    base_module.run = fake_run
    base_module.run_with_status = fake_run_with_status
    scenario.prepare_healthy_baseline()
    assert scenario._healthy_baseline_prepared is True
    scenario.inject_fault()
    assert scenario.state == "bad"
    assert scenario._healthy_baseline_prepared is False
finally:
    base_module.run = original_run
    base_module.run_with_status = original_run_with_status

# A target left stopped by an interrupted prior run is restarted before the
# next scenario's healthy baseline is captured.
restart_scenario = _LifecycleScenario()
restart_scenario.repair_containers = ("target-node",)
restart_calls = []
target_running = False
original_run_with_status = base_module.run_with_status
try:
    def fake_container_status(command, timeout=180):
        global target_running
        restart_calls.append(command)
        if command.startswith("docker inspect"):
            return 0, "true\n" if target_running else "false\n"
        if command == "docker start target-node":
            target_running = True
            return 0, "target-node\n"
        return 1, "unexpected"

    base_module.run_with_status = fake_container_status
    restart_scenario._ensure_repair_containers_running()
finally:
    base_module.run_with_status = original_run_with_status

assert target_running is True
assert "docker start target-node" in restart_calls

# BENCHMARK_SEED produces stable variants without hard-coding one fault value.
old_seed = os.environ.get("BENCHMARK_SEED")
try:
    os.environ["BENCHMARK_SEED"] = "contract-seed"
    first = DnsFailureScenario()
    second = DnsFailureScenario()
    assert first.scenario_seed == second.scenario_seed
    assert first.bad_nameserver == second.bad_nameserver
finally:
    if old_seed is None:
        os.environ.pop("BENCHMARK_SEED", None)
    else:
        os.environ["BENCHMARK_SEED"] = old_seed

# Startup convergence probes must support both routing backends without relying
# on a topology-specific container name.
original_backend_containers = cli_module._backend_containers
original_docker_exec = cli_module._docker_exec
try:
    cli_module._backend_containers = lambda backend, limit=6: [f"{backend}-r1"]

    def fake_docker_exec(container, *args, timeout=5):
        if container == "bird-r1":
            return "u_peer BGP master up 2026-01-01 Established\n"
        return '{"ipv4Unicast":{"peers":{"10.0.0.2":{"state":"Established"}}}}'

    cli_module._docker_exec = fake_docker_exec
    established, backends = cli_module.count_established_bgp_sessions()
    assert established == 2
    assert backends == ["bird", "frr"]
finally:
    cli_module._backend_containers = original_backend_containers
    cli_module._docker_exec = original_docker_exec


class _Completed:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


original_subprocess_run = cli_module.subprocess.run
try:
    def fake_compose_run(command, **_kwargs):
        if "config" in command:
            return _Completed("router\nhost\n")
        if "ps" in command:
            return _Completed("container-a\ncontainer-b\n")
        if "inspect" in command:
            return _Completed("""[
                {
                    "Name": "/router",
                    "State": {
                        "Running": true,
                        "Status": "running",
                        "ExitCode": 0
                    },
                    "Config": {"Labels": {"org.seedsecuritylabs.seedemu.meta.role": "Router"}}
                },
                {
                    "Name": "/host",
                    "State": {
                        "Running": true,
                        "Status": "running",
                        "ExitCode": 0
                    },
                    "Config": {"Labels": {"org.seedsecuritylabs.seedemu.meta.role": "Host"}}
                }
            ]""")
        raise AssertionError(command)

    cli_module.subprocess.run = fake_compose_run
    assert cli_module.wait_for_topology_containers(
        "B00_mini_internet",
        max_wait=1,
    )
finally:
    cli_module.subprocess.run = original_subprocess_run
