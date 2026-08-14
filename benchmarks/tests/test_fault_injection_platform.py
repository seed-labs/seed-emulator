"""Contract, recovery, coverage and scale tests for FaultSpec v1."""

import json
from pathlib import Path
import sys
import tempfile
import time


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.faults.adapters import compile_template_faults  # noqa: E402
from generator.faults.compiler import compile_fault, compile_fault_set  # noqa: E402
from generator.faults.coverage import measure_coverage, select_combinations  # noqa: E402
from generator.faults import drivers as drivers_module  # noqa: E402
from generator.faults.drivers import get_driver  # noqa: E402
from generator.faults.journal import FaultExecutor  # noqa: E402
from generator.faults.models import CompiledFaultPlan, FaultSpec  # noqa: E402
from generator.faults.software import discover_software_fault_specs  # noqa: E402
from generator.templates import (  # noqa: E402
    _bird_asn_candidate, _dns_candidate, _container_candidate,
    _random_acl_candidate, _random_dual_candidate, render_scenario,
)
from generator.topology.bindings import bind_fault_component  # noqa: E402


def capabilities(size=6):
    assets = []
    for index in range(size):
        asn = 64512 + index // 2
        role = "BorderRouter" if index % 2 == 0 else "Host"
        assets.append({
            "container": f"node{index}", "asn": asn, "role": role,
            "interfaces": [{"name": "lan0", "address": f"10.0.{index}.2/24"}],
        })
    return {"topology_fingerprint": "f" * 64, "assets": assets}


def spec(fault_id, fault_type, container, parameters=None, *, max_assets=3):
    return FaultSpec(
        fault_id=fault_id, fault_type=fault_type,
        selector={"container": container}, parameters=parameters or {},
        expectations={"must_break": [fault_id], "must_preserve": ["observer"]},
        safety={"max_affected_assets": max_assets, "max_affected_asns": max_assets,
                "protected_assets": ["observer"], "require_recovery": True},
        seed="contract-seed", schedule={"at_seconds": 0, "duration_seconds": 30},
    )


def software_capabilities():
    value = capabilities(2)
    value["assets"][1]["software"] = [{
        "schema_version": 1,
        "software_id": "jq_tools",
        "packages": ["jq"],
        "resolved_packages": ["jq", "python3-minimal"],
        "capabilities": ["json.query.v1"],
        "managed_files": [{"path": "/etc/jq/benchmark.conf", "mode": "0644"}],
        "fault_profiles": [
            {
                "profile_id": "wrong_mode",
                "fault_type": "software.config.replace",
                "parameters": {
                    "path": "/etc/jq/benchmark.conf",
                    "healthy_value": "mode=healthy",
                    "faulty_value": "mode=broken",
                },
            },
            {
                "profile_id": "disable_binary",
                "fault_type": "software.executable.disabled",
                "parameters": {"path": "/usr/bin/jq", "expected_mode": "0755"},
            },
        ],
    }]
    return value


# FaultSpec is strict, round-trippable, capability-selected and deterministic.
container_spec = spec("stop_node1", "container.stopped", "node1")
assert FaultSpec.from_dict(container_spec.to_dict()) == container_spec
first = compile_fault(container_spec, capabilities())
second = compile_fault(container_spec, capabilities())
assert first == second
assert len(first.plan_fingerprint) == 64
assert CompiledFaultPlan.from_dict(first.to_dict()) == first
tampered = first.to_dict()
tampered["affected_assets"] = ["outside"]
try:
    CompiledFaultPlan.from_dict(tampered)
    raise AssertionError("tampered compiled plan was accepted")
except ValueError as exc:
    assert "fingerprint" in str(exc)

# Software capabilities automatically produce safe, deterministic FaultSpecs.
software_specs_a = discover_software_fault_specs(
    software_capabilities(), master_seed="software-seed"
)
software_specs_b = discover_software_fault_specs(
    software_capabilities(), master_seed="software-seed"
)
assert software_specs_a == software_specs_b and len(software_specs_a) == 2
software_plans = tuple(
    compile_fault(item, software_capabilities()) for item in software_specs_a
)
software_actions = {plan.actions[0].driver: plan.actions[0] for plan in software_plans}
config_action = software_actions["software.config.replace"]
assert "python3 -c" in config_action.inject_command
assert "/etc/jq/benchmark.conf" in config_action.inject_command
assert "mode=healthy" not in config_action.inject_command
assert "mode=broken" not in config_action.inject_command
assert config_action.cleanup_command != config_action.inject_command
executable_action = software_actions["software.executable.disabled"]
assert "chmod 000" in executable_action.inject_command
assert "chmod 0755" in executable_action.cleanup_command
assert executable_action.targets == ("node1",)
hostile_capabilities = json.loads(json.dumps(software_capabilities()))
hostile_capabilities["assets"][1]["software"][0]["fault_profiles"][1][
    "parameters"
]["path"] = "/usr/bin/python3"
hostile_spec = next(
    item for item in discover_software_fault_specs(
        hostile_capabilities, master_seed="hostile"
    ) if item.fault_type == "software.executable.disabled"
)
try:
    compile_fault(hostile_spec, hostile_capabilities)
    raise AssertionError("protected software executable capability was accepted")
except ValueError as exc:
    assert "unsafe" in str(exc)

# Impact, protected-target and resource-lock conflict gates fail closed.
try:
    compile_fault(spec("stop_observer", "container.stopped", "observer"), capabilities())
    raise AssertionError("missing target was accepted")
except ValueError:
    pass
same_a = spec("stop_same_a", "container.stopped", "node1")
same_b = spec("stop_same_b", "container.stopped", "node1")
try:
    compile_fault_set((same_a, same_b), capabilities())
    raise AssertionError("conflicting resource locks were accepted")
except ValueError as exc:
    assert "conflict" in str(exc)

# tc/netem covers delay, loss, rate limiting, jitter and combined profiles.
for index, values in enumerate((
    {"interface": "lan0", "delay_ms": 100, "jitter_ms": 0,
     "loss_percent": 0, "rate_kbit": 0},
    {"interface": "lan0", "delay_ms": 0, "jitter_ms": 0,
     "loss_percent": 25, "rate_kbit": 0},
    {"interface": "lan0", "delay_ms": 0, "jitter_ms": 0,
     "loss_percent": 0, "rate_kbit": 512},
    {"interface": "lan0", "delay_ms": 80, "jitter_ms": 20,
     "loss_percent": 5, "rate_kbit": 1024},
)):
    plan = compile_fault(spec(f"netem_{index}", "network.netem", "node1", values), capabilities())
    command = plan.actions[0].inject_command
    assert "tc qdisc replace" in command
    if values["jitter_ms"]:
        assert f"{values['jitter_ms']}ms" in command

# Migrated templates retain their externally visible injection/fix semantics.
cases = (
    ("bird_wrong_asn", _bird_asn_candidate(0, 1)),
    ("dns_nameserver", _dns_candidate(0, 1)),
    ("container_stopped", _container_candidate(0, 1)),
    ("random_complex_transit_acl", _random_acl_candidate(0, 1)),
    ("random_complex_dual_bgp_acl", _random_dual_candidate(0, 1)),
)
for template_id, parameters in cases:
    plan = compile_template_faults(template_id, parameters)
    assert all(action.inject_command and action.cleanup_command for action in plan.actions)
    assert all(action.snapshot_command for action in plan.actions)

# Every plugin shares bounded infrastructure retries.  A snap transient is
# retried, while a real workload failure returns immediately to the executor.
driver = get_driver("container.stopped")
action = first.actions[0]
retry_calls = []
original_driver_sleep = drivers_module.time.sleep
try:
    def transient_runner(command, timeout):
        retry_calls.append((command, timeout))
        if len(retry_calls) < 3:
            return 46, "transient scope not created in 10s"
        return 0, "ok"

    drivers_module.time.sleep = lambda _seconds: None
    assert driver.inject(action, transient_runner) == (0, "ok")
finally:
    drivers_module.time.sleep = original_driver_sleep
assert len(retry_calls) == 3

real_failure_calls = []
assert driver.inject(
    action,
    lambda command, timeout: real_failure_calls.append(command) or (1, "denied"),
) == (1, "denied")
assert len(real_failure_calls) == 1

# Journal persists the risky pre-mutation transition and recovers in reverse.
commands = []
inspect_count = 0
container_running = True
def successful_runner(command, timeout):
    global inspect_count, container_running
    commands.append(command)
    if "docker stop" in command:
        container_running = False
    elif "docker start" in command:
        container_running = True
    if "docker inspect" in command:
        inspect_count += 1
        return 0, str(container_running).lower()
    return 0, "ok"

with tempfile.TemporaryDirectory() as temporary:
    executor = FaultExecutor(Path(temporary), successful_runner)
    journal_path = executor.inject(first, "successful")
    assert json.loads(journal_path.read_text())["status"] == "active"
    executor.recover(first, "successful")
    assert json.loads(journal_path.read_text())["status"] == "recovered"
    assert first.actions[0].cleanup_command in commands
    assert commands[-1] == first.actions[0].active_check_command

failure_calls = []
def failing_runner(command, timeout):
    failure_calls.append(command)
    if "docker stop" in command:
        return 1, "injected then connection lost"
    return 0, "true"

with tempfile.TemporaryDirectory() as temporary:
    executor = FaultExecutor(Path(temporary), failing_runner)
    try:
        executor.inject(first, "interrupted")
        raise AssertionError("failed injection was accepted")
    except RuntimeError:
        pass
    state = json.loads((Path(temporary) / "interrupted.json").read_text())
    assert state["status"] == "recovered"
    assert first.actions[0].cleanup_command in failure_calls

# Automatic combinations are deterministic, conflict free and coverage aware.
candidates = (
    spec("auto_stop_1", "container.stopped", "node1"),
    spec("auto_stop_3", "container.stopped", "node3"),
    spec("auto_netem_1", "network.netem", "node1", {
        "interface": "lan0", "delay_ms": 100, "jitter_ms": 10,
        "loss_percent": 2, "rate_kbit": 0,
    }),
    spec("auto_netem_3", "network.netem", "node3", {
        "interface": "lan0", "delay_ms": 0, "jitter_ms": 0,
        "loss_percent": 10, "rate_kbit": 0,
    }),
)
selected_a = select_combinations(candidates, capabilities(), count=3, master_seed="x")
selected_b = select_combinations(candidates, capabilities(), count=3, master_seed="x")
assert selected_a == selected_b
coverage = measure_coverage(selected_a, capabilities()).to_dict()
assert coverage["scores"]["weighted_total"] > 0
assert len(coverage["pair_signatures"]) >= 1

# Planner performance is linear in capability inventory; bounded selection does
# not perform all-pairs connectivity checks, even at 10,000 assets.
for size, limit in ((1000, 2.0), (10000, 8.0)):
    large = capabilities(size)
    start = time.perf_counter()
    plan = compile_fault(
        FaultSpec(
            fault_id=f"scale_{size}", fault_type="container.stopped",
            selector={"role": "Host", "choose": 1}, parameters={},
            expectations={"must_break": ["one-host"], "must_preserve": ["sampled"]},
            safety={"max_affected_assets": 1, "max_affected_asns": 1,
                    "protected_assets": [], "require_recovery": True},
            seed="scale-seed", schedule={"at_seconds": 0},
        ),
        large,
    )
    elapsed = time.perf_counter() - start
    assert len(plan.affected_assets) == 1 and elapsed < limit, (size, elapsed)
