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
from generator.templates import TEMPLATES, render_scenario  # noqa: E402
from generator.validator import validate_manifest, validate_scenario_spec  # noqa: E402
import benchmark_cli as cli_module  # noqa: E402
from benchmark_cli import can_reuse_topology_between_scenarios  # noqa: E402
import scenarios.base as base_module  # noqa: E402


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

serial_build_calls = []
original_run_argv_checked = cli_module.run_argv_checked
with tempfile.TemporaryDirectory() as build_directory:
    build_root = Path(build_directory)
    compose_root = build_root / "compose-project"
    service_a = build_root / "service_a"
    service_b = build_root / "service_b"
    compose_root.mkdir()
    service_a.mkdir()
    service_b.mkdir()
    (service_a / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (service_b / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    config_document = {
        "name": "probe",
        "services": {
            "service_a": {
                "build": {
                    "context": str(service_a),
                    "dockerfile": "Dockerfile",
                },
            },
            "service_b": {
                "build": {
                    "context": str(service_b),
                    "dockerfile": "Containerfile",
                },
                "image": "custom/service_b:test",
            },
            "external": {"image": "external/service:latest"},
        },
    }
    built_images = set()

    def serial_run_argv_checked(args, timeout=180, *, cwd=None, env=None):
        serial_build_calls.append((tuple(args), timeout, cwd, env))
        if tuple(args) == (
            "docker", "compose", "config", "--format", "json",
        ):
            return json.dumps(config_document)
        if tuple(args)[:5] == (
            "docker", "image", "inspect", "--format", "{{.Id}}",
        ):
            expected = set(args[5:])
            if expected <= built_images:
                return "\n".join("sha256:present" for _item in expected)
            raise RuntimeError("No such image")
        if tuple(args)[:3] == ("docker", "image", "inspect"):
            if args[-1] in built_images:
                return "present"
            raise RuntimeError("No such image")
        if tuple(args)[-1] == str(service_a) and "--no-cache" not in args:
            raise RuntimeError("parent snapshot sha256:broken does not exist")
        if tuple(args)[-1] == str(service_a):
            built_images.add("probe-service_a:latest")
        if tuple(args)[-1] == str(service_b):
            built_images.add("custom/service_b:test")
        return "ok"

    try:
        cli_module.run_argv_checked = serial_run_argv_checked
        serial_result = cli_module.build_compose_services_serially(
            str(compose_root),
            timeout_per_service=77,
        )
        first_call_count = len(serial_build_calls)
        cached_result = cli_module.build_compose_services_serially(
            str(compose_root),
            timeout_per_service=77,
        )
        cached_calls = serial_build_calls[first_call_count:]
        built_images.remove("custom/service_b:test")
        missing_result = cli_module.build_compose_services_serially(
            str(compose_root),
            timeout_per_service=77,
            verify_images=True,
        )
        (service_b / "payload.txt").write_text("changed\n", encoding="utf-8")
        changed_result = cli_module.build_compose_services_serially(
            str(compose_root),
            timeout_per_service=77,
        )
    finally:
        cli_module.run_argv_checked = original_run_argv_checked

assert serial_result["service_count"] == 2
assert serial_result["built_services"] == ("service_a", "service_b")
assert serial_result["repaired_services"] == ("service_a",)
assert serial_result["cache_hit"] is False
assert len(serial_result["fingerprint"]) == 64
assert cached_result["cache_hit"] is True
assert cached_result["built_services"] == ()
assert not any(call[0][:2] == ("docker", "build") for call in cached_calls)
assert missing_result["cache_hit"] is False
assert missing_result["built_services"] == ("service_b",)
assert changed_result["cache_hit"] is False
assert changed_result["built_services"] == ("service_a", "service_b")
docker_build_calls = [
    item for item in serial_build_calls if item[0][:2] == ("docker", "build")
]
assert docker_build_calls[0][0][:2] == ("docker", "build")
assert "--no-cache" not in docker_build_calls[0][0]
assert docker_build_calls[0][0][-1] == str(service_a)
assert docker_build_calls[1][0][:3] == ("docker", "build", "--no-cache")
assert docker_build_calls[1][0][-1] == str(service_a)
assert "custom/service_b:test" in docker_build_calls[2][0]
assert docker_build_calls[2][0][-1] == str(service_b)
assert all(item[3]["DOCKER_BUILDKIT"] == "1" for item in serial_build_calls)

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
    "cascading_network_bgp",
    "container_stopped",
    "dns_nameserver",
    "dual_bgp_ospf",
    "dual_dns_network",
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
    "random_complex_dual_bgp_acl",
    "random_complex_transit_acl",
}
assert all(item.convergence_timeout in {240, 300} for item in random_suite.scenarios)
random_spec = next(
    item
    for item in random_suite.scenarios
    if item.template_id == "random_complex_transit_acl"
)
random_rendered = render_scenario(random_spec)
assert "iptables -I OUTPUT" in random_rendered.inject_command
assert "SEED_RANDOM_COMPLEX_ACL" in random_rendered.fix_command
assert "ping -I ix201" in random_rendered.verify_command
assert random_spec.parameters["destination_asn"] in {21, 22, 24, 25, 107, 113}
assert random_spec.repair_containers == (
    random_spec.parameters["source_router"],
)
random_scenario = scenario_class_from_spec(random_spec)()
assert random_scenario.check_verified("2 packets transmitted, 2 received, 0% packet loss")
assert not random_scenario.check_verified("2 packets transmitted, 0 received, 100% packet loss")

random_dual_spec = next(
    item
    for item in random_suite.scenarios
    if item.template_id == "random_complex_dual_bgp_acl"
)
random_dual_rendered = render_scenario(random_dual_spec)
assert random_dual_spec.fault_relationship == "independent"
assert len(random_dual_spec.expected_root_causes) == 2
assert len(random_dual_spec.fault_components) == 2
assert [
    item.component_id
    for item in sorted(
        random_dual_rendered.components,
        key=lambda component: component.inject_order,
    )
] == ["random_bird_wrong_asn", "random_transit_acl"]
assert "config_summary" not in random_dual_rendered.verify_command
assert "iptables -C OUTPUT" in random_dual_rendered.components[1].fault_check_command

dual_bgp_spec = next(
    item for item in first.scenarios if item.template_id == "dual_bgp_ospf"
)
dual_bgp_rendered = render_scenario(dual_bgp_spec)
assert dual_bgp_spec.fault_type == "multiple_faults"
assert dual_bgp_spec.fault_relationship == "independent"
assert len(dual_bgp_spec.expected_root_causes) == 2
assert {item.category for item in dual_bgp_spec.expected_root_causes} == {
    "wrong_asn",
    "missing_ospf_adjacency",
}
assert [item.inject_order for item in dual_bgp_spec.fault_components] == [0, 1]
assert [item.cleanup_order for item in dual_bgp_spec.fault_components] == [1, 0]
assert dual_bgp_rendered.fix_command.startswith(
    dual_bgp_rendered.components[1].cleanup_command
)

component_scenario = scenario_class_from_spec(dual_bgp_spec)()
component_scenario._healthy_baseline_prepared = True
component_calls = []
original_base_status = base_module.run_with_status
original_base_run = base_module.run
original_runtime_sleep = __import__("generator.runtime", fromlist=["time"]).time.sleep
runtime_module = __import__("generator.runtime", fromlist=["time"])
from generator.faults.journal import FaultExecutor  # noqa: E402
original_fault_inject = FaultExecutor.inject
try:
    def component_status(command, timeout=120):
        component_calls.append(("status", command, timeout))
        for component in dual_bgp_rendered.components:
            if command == component.fault_check_command:
                return 0, component.fault_verifier_value
        return 0, "injected"

    def component_run(command, timeout=120):
        component_calls.append(("run", command, timeout))
        return ""

    def compiled_inject(executor, plan, execution_id):
        component_calls.extend(
            ("compiled", action.action_id, 0) for action in plan.actions
        )
        return Path("/tmp/generated-test-journal.json")

    base_module.run_with_status = component_status
    base_module.run = component_run
    FaultExecutor.inject = compiled_inject
    runtime_module.time.sleep = lambda _seconds: None
    component_scenario.inject_fault()
finally:
    base_module.run_with_status = original_base_status
    base_module.run = original_base_run
    FaultExecutor.inject = original_fault_inject
    runtime_module.time.sleep = original_runtime_sleep
assert [
    command
    for kind, command, _timeout in component_calls
    if kind == "compiled"
] == [
    "bird_wrong_asn",
    "ospf_wrong_area",
]

cascade_spec = next(
    item
    for item in first.scenarios
    if item.template_id == "cascading_network_bgp"
)
assert cascade_spec.fault_relationship == "cascading"
assert cascade_spec.causal_chain == (
    "docker_network_disconnect",
    "interface_removed",
    "external_peer_unreachable",
    "external_bgp_path_unusable",
)
assert len(cascade_spec.expected_root_causes) == 1

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
            "root_causes": [
                {
                    "category": root.category,
                    "target_container": list(root.target_container),
                    "artifact": root.artifact,
                    "faulty_value": root.faulty_value,
                    "expected_value": root.expected_value,
                }
                for root in spec.expected_root_causes
            ],
        }
    )
    assert score["correct"] is True

bad_component = replace(
    dual_bgp_spec.fault_components[1],
    depends_on=("missing_component",),
)
invalid_dependency = replace(
    dual_bgp_spec,
    fault_components=(dual_bgp_spec.fault_components[0], bad_component),
)
try:
    validate_scenario_spec(invalid_dependency)
    raise AssertionError("unknown component dependency was accepted")
except ValueError as exc:
    assert "dependency" in str(exc)

original_dual_template = TEMPLATES["dual_bgp_ospf"]
try:
    original_renderer = original_dual_template.renderer

    def unsafe_check_renderer(parameters):
        rendered = original_renderer(parameters)
        unsafe_component = replace(
            rendered.components[0],
            fault_check_command=(
                f"docker exec {parameters['container']} "
                "sed -i 's/a/b/' /etc/bird/bird.conf"
            ),
        )
        return replace(
            rendered,
            components=(unsafe_component, rendered.components[1]),
        )

    TEMPLATES["dual_bgp_ospf"] = replace(
        original_dual_template,
        renderer=unsafe_check_renderer,
    )
    try:
        validate_scenario_spec(dual_bgp_spec)
        raise AssertionError("mutating component activation check was accepted")
    except ValueError as exc:
        assert "not read-only" in str(exc)
finally:
    TEMPLATES["dual_bgp_ospf"] = original_dual_template

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
