#!/usr/bin/env python3
"""Policy, planning, approval, and isolation tests for unsafe NL mode."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import yaml


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.nl.provider import LLMProvider, ProviderResponse  # noqa: E402
from generator.nl.unsafe_models import UnsafeScenarioPlan, validate_unsafe_provider_output  # noqa: E402
from generator.nl.unsafe_policy import compile_unsafe_policy  # noqa: E402
from generator.nl.unsafe_provider import DeterministicUnsafeProvider  # noqa: E402
from generator.nl.unsafe_session import (  # noqa: E402
    MAX_CAPTURE_BYTES,
    UnsafeNaturalLanguageExecutor,
    UnsafeNaturalLanguagePlanner,
)


TEXT = "Generate an arbitrary private topology and write the required scripts"


def expect_error(function, expected=ValueError):
    try:
        function()
    except expected:
        return
    raise AssertionError(f"expected {expected.__name__}")


def provider_output():
    provider = DeterministicUnsafeProvider(base_image="fixture-base:latest")
    response = provider.complete_structured(
        [{"role": "user", "content": TEXT}], {}, seed="unsafe-test-seed"
    )
    validate_unsafe_provider_output(response.output)
    return response.output


def plan_from(output):
    return UnsafeScenarioPlan.from_provider_output(
        output,
        source_text=TEXT,
        seed="unsafe-test-seed",
        provider_model="deterministic_unsafe:deterministic-unsafe-v1",
    )


base_output = provider_output()
base_plan = plan_from(base_output)
first_policy = compile_unsafe_policy(base_plan, session_label="unsafe_test_session")
second_policy = compile_unsafe_policy(base_plan, session_label="unsafe_test_session")
assert first_policy.policy_fingerprint == second_policy.policy_fingerprint
assert first_policy.sanitized_compose_yaml == second_policy.sanitized_compose_yaml
assert first_policy.effective_limits["service_count"] == 2
assert first_policy.base_images == ("fixture-base:latest",)
assert {step.phase for step in base_plan.steps} == {
    "baseline", "inject", "observe", "recover", "verify",
}

sanitized = yaml.safe_load(first_policy.sanitized_compose_yaml)
assert all(network["driver"] == "bridge" and network["internal"] is True for network in sanitized["networks"].values())
for service_id, service in sanitized["services"].items():
    assert service["build"]["context"] == f"./services/{service_id}"
    assert service["build"]["network"] == "none"
    assert service["build"]["labels"]["benchmark.unsafe.session"] == "unsafe_test_session"
    assert service["privileged"] is False
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["pids_limit"] == 256
    assert service["cpus"] > 0 and service["mem_limit"].endswith("m")
    assert {entry.split(":", 1)[0] for entry in service["tmpfs"]} == {"/tmp", "/run"}
    assert service["labels"]["benchmark.unsafe.session"] == "unsafe_test_session"
    assert service["labels"]["benchmark.unsafe.generated"] == "true"
    assert service["image"].startswith("unsafe-local/unsafe_test_session-")


def mutate_compose(mutator):
    output = copy.deepcopy(base_output)
    compose = yaml.safe_load(output["compose_yaml"])
    mutator(compose)
    output["compose_yaml"] = yaml.safe_dump(compose, sort_keys=True)
    return plan_from(output)


compose_attacks = [
    lambda value: value["services"]["node_a"].update({"privileged": True}),
    lambda value: value["services"]["node_a"].update({"network_mode": "host"}),
    lambda value: value["services"]["node_a"].update({"pid": "host"}),
    lambda value: value["services"]["node_a"].update({"ports": ["8080:80"]}),
    lambda value: value["services"]["node_a"].update({"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}),
    lambda value: value["services"]["node_a"].update({"devices": ["/dev/net/tun"]}),
    lambda value: value["services"]["node_a"].update({"cap_add": ["SYS_ADMIN"]}),
    lambda value: value["networks"]["lab_net"].update({"external": True}),
    lambda value: value["services"]["node_a"].update({"environment": {"ESCAPE": "${HOME}"}}),
    lambda value: value["services"]["node_a"]["build"].update({"context": "."}),
    lambda value: value["services"]["node_a"]["build"].update({"labels": {"benchmark.unsafe.session": "forged"}}),
]
for attack in compose_attacks:
    expect_error(lambda attack=attack: compile_unsafe_policy(
        mutate_compose(attack), session_label="unsafe_test_session"
    ))


dockerfile_attacks = [
    "FROM fixture-base:latest\nVOLUME /host\n",
    "FROM fixture-base:latest\nADD https://example.invalid/a /tmp/a\n",
    "# syntax=evil/frontend:latest\nFROM fixture-base:latest\n",
    "FROM fixture-base:latest\nRUN --security=insecure true\n",
    "FROM fixture-base:latest\nRUN --mount=type=secret true\n",
    "FROM fixture-base:latest\nRUN test -e /var/run/docker.sock\n",
    "FROM fixture-base:latest AS build\nCOPY --from=remote/image /bin/x /bin/x\n",
    "ARG BASE=fixture-base:latest\nFROM ${BASE}\n",
]
for content in dockerfile_attacks:
    output = copy.deepcopy(base_output)
    output["files"][0]["content"] = content
    expect_error(lambda output=output: compile_unsafe_policy(
        plan_from(output), session_label="unsafe_test_session"
    ))

path_attack = copy.deepcopy(base_output)
path_attack["files"][0]["path"] = "services/../escape/Dockerfile"
expect_error(lambda: compile_unsafe_policy(plan_from(path_attack), session_label="unsafe_test_session"))

schema_attack = copy.deepcopy(base_output)
schema_attack["host_shell"] = "id"
expect_error(lambda: validate_unsafe_provider_output(schema_attack))

budget_attack = copy.deepcopy(base_output)
budget_attack["budget"]["max_services"] = 33
expect_error(lambda: validate_unsafe_provider_output(budget_attack))

disk_budget_attack = copy.deepcopy(base_output)
disk_budget_attack["budget"]["max_disk_mb"] = 16
expect_error(lambda: plan_from(disk_budget_attack))

phase_order_attack = copy.deepcopy(base_output)
phase_order_attack["steps"][1], phase_order_attack["steps"][3] = (
    phase_order_attack["steps"][3], phase_order_attack["steps"][1],
)
expect_error(lambda: plan_from(phase_order_attack))


class MaliciousProvider(LLMProvider):
    provider_id = "malicious_unsafe"
    model_id = "malicious-v1"

    def complete_structured(self, messages, output_schema, *, seed):
        output = copy.deepcopy(base_output)
        compose = yaml.safe_load(output["compose_yaml"])
        compose["services"]["node_a"]["privileged"] = True
        output["compose_yaml"] = yaml.safe_dump(compose, sort_keys=True)
        return ProviderResponse(
            provider=self.provider_id,
            model=self.model_id,
            output=output,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            latency_ms=0,
            response_fingerprint=hashlib.sha256(b"malicious").hexdigest(),
        )


class InvalidSchemaProvider(LLMProvider):
    provider_id = "invalid_schema_unsafe"
    model_id = "invalid-schema-v1"

    def complete_structured(self, messages, output_schema, *, seed):
        output = {**copy.deepcopy(base_output), "host_shell": "id"}
        return ProviderResponse(
            provider=self.provider_id, model=self.model_id, output=output,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            latency_ms=0,
            response_fingerprint=hashlib.sha256(b"invalid-schema").hexdigest(),
        )


with tempfile.TemporaryDirectory(prefix="unsafe-nl-test-") as temporary:
    root = Path(temporary)
    sessions = root / "sessions"
    planner = UnsafeNaturalLanguagePlanner(BENCHMARKS_DIR, sessions)
    result = planner.plan(
        TEXT,
        provider=DeterministicUnsafeProvider(base_image="fixture-base:latest"),
        seed="planner-seed",
        session_id="unsafe_planner_test",
    )
    assert result["status"] == "ready"
    assert result["provider_invoked"] is True
    assert result["preview"]["mode"] == "plan_only_no_docker_state_change"
    assert result["preview"]["execution_authorized"] is False
    assert result["preview"]["unsafe_generated"] is True
    assert result["preview"]["qualification_status"] == "forbidden"
    assert result["preview"]["publication_status"] == "forbidden"
    assert "compose" in result["preview"]["sanitized_compose_yaml"] or "services:" in result["preview"]["sanitized_compose_yaml"]
    assert result["preview"]["generated_files"]
    assert result["preview"]["shell_steps"]
    session = Path(result["session"])
    challenge = json.loads((session / "unsafe_approval_challenge.json").read_text(encoding="utf-8"))
    assert result["approval_token"] not in (session / "unsafe_approval_challenge.json").read_text(encoding="utf-8")
    assert challenge["token_sha256"] == hashlib.sha256(result["approval_token"].encode()).hexdigest()
    assert challenge["qualification_authorized"] is False
    assert challenge["publication_authorized"] is False
    assert not (session / "unsafe_execution").exists()

    executor = UnsafeNaturalLanguageExecutor(BENCHMARKS_DIR, sessions)
    expect_error(lambda: executor.execute(
        Path(result["unsafe_plan"]), result["approval_token"],
        acknowledge_arbitrary_code=False,
    ))
    expect_error(lambda: executor.execute(
        Path(result["unsafe_plan"]), "wrong-token",
        acknowledge_arbitrary_code=True,
    ))
    challenge_after = json.loads((session / "unsafe_approval_challenge.json").read_text(encoding="utf-8"))
    assert challenge_after["consumed"] is False
    assert not (session / "unsafe_execution.claim").exists()

    rejected = planner.plan(
        TEXT,
        provider=MaliciousProvider(),
        seed="malicious-seed",
        session_id="unsafe_policy_rejection",
    )
    assert rejected["status"] == "policy_rejected"
    rejected_session = Path(rejected["session"])
    assert not (rejected_session / "unsafe_approval_challenge.json").exists()
    assert not (rejected_session / "unsafe_execution").exists()

    schema_rejected = planner.plan(
        TEXT,
        provider=InvalidSchemaProvider(),
        seed="schema-rejection-seed",
        session_id="unsafe_schema_rejection",
    )
    assert schema_rejected["status"] == "schema_rejected"
    schema_session = Path(schema_rejected["session"])
    assert (schema_session / "provider_response.json").is_file()
    assert (schema_session / "unsafe_schema_rejection.json").is_file()
    assert (schema_session / "unsafe_audit.json").is_file()
    assert not (schema_session / "unsafe_approval_challenge.json").exists()

    output_evidence = root / "bounded_output"
    output_evidence.mkdir()
    command_records = []
    bounded = executor._run(
        name="output_limit",
        args=[
            os.sys.executable, "-c",
            f"import sys; sys.stdout.write('x' * {MAX_CAPTURE_BYTES + 1024})",
        ],
        cwd=root,
        timeout=30,
        evidence_dir=output_evidence,
        commands=command_records,
    )
    assert bounded.returncode == 126
    assert command_records[0]["output_budget_exceeded"] is True
    assert (output_evidence / "output_limit.stdout.log").stat().st_size <= MAX_CAPTURE_BYTES + 32

print("unsafe natural-language generator tests: PASS")
