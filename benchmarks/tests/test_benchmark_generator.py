"""Contracts for deterministic, safe, large-suite generation."""

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.agent import BenchmarkGeneratorAgent  # noqa: E402
from generator.contracts import inspect_contracts  # noqa: E402
from generator.models import GenerationJob, SuiteManifest  # noqa: E402
from generator.planner import plan_suite  # noqa: E402
from generator.runtime import scenario_class_from_spec  # noqa: E402
from generator.storage import validate_manifest_file, write_manifest  # noqa: E402
from generator.templates import render_scenario  # noqa: E402
from generator.validator import validate_manifest, validate_scenario_spec  # noqa: E402
import benchmark_cli as cli_module  # noqa: E402
from benchmark_cli import can_reuse_topology_between_scenarios  # noqa: E402


snapshot = inspect_contracts(BENCHMARKS_DIR)
assert "get_inject_cmd" in snapshot.base_methods
assert "--repair-eval" in snapshot.cli_options
assert len(snapshot.sha256) == 64
assert can_reuse_topology_between_scenarios(
    SimpleNamespace(repair_eval=False, validate_only=True),
    "B00_mini_internet",
)
assert not can_reuse_topology_between_scenarios(
    SimpleNamespace(repair_eval=False, validate_only=False),
    "B00_mini_internet",
)

retry_calls = []
original_run_checked = cli_module.run_checked
original_sleep = cli_module.time.sleep
try:
    def transient_run_checked(command, timeout=180):
        retry_calls.append((command, timeout))
        if len(retry_calls) < 3:
            raise RuntimeError("transient build race")
        return "ok"

    cli_module.run_checked = transient_run_checked
    cli_module.time.sleep = lambda _seconds: None
    assert cli_module.run_checked_with_retries(
        "docker compose build",
        timeout=99,
        attempts=3,
    ) == "ok"
finally:
    cli_module.run_checked = original_run_checked
    cli_module.time.sleep = original_sleep
assert len(retry_calls) == 3

agent = BenchmarkGeneratorAgent(BENCHMARKS_DIR)
job = GenerationJob(
    suite_id="generator_contract_suite",
    case_count=100,
    master_seed="contract-seed-20260809",
)
with tempfile.TemporaryDirectory() as planning_directory:
    planning_root = Path(planning_directory)
    first = plan_suite(
        job,
        contract_sha256=snapshot.sha256,
        benchmarks_dir=planning_root,
    )
    second = plan_suite(
        job,
        contract_sha256=snapshot.sha256,
        benchmarks_dir=planning_root,
    )
assert first.to_dict() == second.to_dict()
assert len(first.scenarios) == 100
assert len({item.name for item in first.scenarios}) == 100
assert len({item.fingerprint for item in first.scenarios}) == 100
assert {item.template_id for item in first.scenarios} == {
    "bird_wrong_asn",
    "container_stopped",
    "dns_nameserver",
    "ipv6_connected_route",
}
batches = agent.build_batches(first, batch_size=7)
assert len(batches) == 15
assert sum(len(item["scenarios"]) for item in batches) == 100
assert all(len(item["scenarios"]) <= 7 for item in batches)
assert all(item["topology"] == "B00_mini_internet" for item in batches)

with tempfile.TemporaryDirectory() as planning_directory:
    random_suite = plan_suite(
        GenerationJob(
            suite_id="random_complex_contract_suite",
            case_count=10,
            master_seed="random-contract-seed",
            topology="RANDOM_COMPLEX_INTERNET",
        ),
        contract_sha256=snapshot.sha256,
        benchmarks_dir=Path(planning_directory),
    )
validate_manifest(random_suite)
assert len(random_suite.scenarios) == 10
assert {item.template_id for item in random_suite.scenarios} == {
    "random_complex_transit_acl"
}
assert all(item.convergence_timeout == 240 for item in random_suite.scenarios)
random_spec = random_suite.scenarios[0]
random_rendered = render_scenario(random_spec)
assert "iptables -I FORWARD" in random_rendered.inject_command
assert "SEED_RANDOM_COMPLEX_ACL" in random_rendered.fix_command
assert random_spec.repair_containers == (
    random_spec.parameters["source_router"],
)
random_scenario = scenario_class_from_spec(random_spec)()
assert random_scenario.check_verified("2 packets transmitted, 2 received, 0% packet loss")
assert not random_scenario.check_verified("2 packets transmitted, 0 received, 100% packet loss")

for spec in first.scenarios:
    validate_scenario_spec(spec)
    scenario_class = scenario_class_from_spec(
        spec,
        suite_id=first.suite_id,
        contract_sha256=first.contract_sha256,
    )
    scenario = scenario_class()
    rendered = render_scenario(spec)
    assert scenario.name == spec.name
    assert scenario.topology == spec.topology
    assert scenario.get_inject_cmd() == rendered.inject_command
    assert scenario.get_verify_cmd() == rendered.verify_command
    assert scenario.get_fix_cmd() == rendered.fix_command
    assert scenario.generated_suite_id == first.suite_id
    assert scenario.generation_fingerprint == spec.fingerprint
    assert scenario.check_verified("") is False
    if rendered.verifier_kind == "contains":
        assert scenario.check_verified(rendered.verifier_value)
    elif rendered.verifier_kind == "equals":
        assert scenario.check_verified(rendered.verifier_value.upper())
    else:
        raise AssertionError(rendered.verifier_kind)
    score = scenario.score_diagnosis(
        {
            "category": spec.fault_type,
            "target_container": list(spec.diagnosis_targets),
            "artifact": spec.diagnosis_artifact,
            "faulty_value": spec.diagnosis_faulty_value,
            "expected_value": spec.diagnosis_expected_value,
        }
    )
    assert score["correct"] is True

invalid = replace(first.scenarios[0], fingerprint="0" * 64)
try:
    validate_scenario_spec(invalid)
    raise AssertionError("invalid fingerprint was accepted")
except ValueError as exc:
    assert "fingerprint" in str(exc)

invalid_name = replace(first.scenarios[0], name="wrong_asn_01")
try:
    validate_scenario_spec(invalid_name)
    raise AssertionError("generated scenario escaped the gen_ namespace")
except ValueError as exc:
    assert "gen_" in str(exc)

validate_manifest(first)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    path = write_manifest(root, first)
    assert path == root / "specs" / first.suite_id / "manifest.json"
    loaded = validate_manifest_file(path)
    assert loaded.to_dict() == first.to_dict()
    try:
        write_manifest(root, first)
        raise AssertionError("manifest overwrite did not require force")
    except FileExistsError:
        pass
    replaced_path = write_manifest(root, first, force=True)
    assert replaced_path == path

try:
    agent.plan(
        GenerationJob(
            suite_id="bad",
            case_count=10001,
            master_seed="x",
        )
    )
    raise AssertionError("oversized job was accepted")
except ValueError as exc:
    assert "case_count" in str(exc)
