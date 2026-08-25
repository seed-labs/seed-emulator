"""Contracts for multi-agent bundle compilation and no-AI lifecycle."""

import json
from pathlib import Path
import sys
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.bundle.artifacts import AgentArtifact, ArtifactStore  # noqa: E402
from generator.bundle.compiler import BundleCompiler  # noqa: E402
from generator.bundle.coordinator import AgentTask, BenchmarkCoordinator  # noqa: E402
from generator.bundle.lifecycle import BundleLifecycleExecutor  # noqa: E402
from generator.bundle.models import CompiledBenchmarkBundle  # noqa: E402
from generator.bundle.pilot import pilot_capabilities, write_pilot_artifacts  # noqa: E402
from generator.bundle.qualification import qualify_bundle  # noqa: E402
from generator.bundle.scale import validate_bundle_scales  # noqa: E402
from generator.faults.compiler import compile_fault  # noqa: E402
from generator.faults.models import FaultSpec  # noqa: E402


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    store, spec = write_pilot_artifacts(root / "artifacts")
    capabilities = pilot_capabilities()
    compiler = BundleCompiler(BENCHMARKS_DIR, store)
    first = compiler.compile(spec, capabilities=capabilities)
    second = compiler.compile(spec, capabilities=capabilities)
    assert first == second
    assert first.safety_review["approved"] is True
    assert first.generator_contract_sha256 == first.public_bundle[
        "generator_contract_sha256"
    ]
    assert first.public_bundle["scenario_metadata_included"] is False
    public_text = json.dumps(first.public_bundle)
    for marker in (
        "fault_id", "fault_type", "inject_command", "cleanup_command",
        "faulty_value", "expected_value",
    ):
        assert marker not in public_text
    bundle_path = compiler.write(first, root / "compiled.json")
    loaded = CompiledBenchmarkBundle.from_dict(json.loads(bundle_path.read_text()))
    assert loaded.bundle_fingerprint == first.bundle_fingerprint
    assert loaded.public_bundle == first.public_bundle
    tampered = loaded.to_dict()
    tampered["public_bundle"]["leak"] = "changed"
    try:
        CompiledBenchmarkBundle.from_dict(tampered)
        raise AssertionError("tampered bundle was accepted")
    except ValueError as exc:
        assert "fingerprint" in str(exc)

    # A fake Docker runtime proves the entire no-AI lifecycle without invoking
    # an Agent or mutating the host running this contract test.
    running = {item["container"]: True for item in capabilities["assets"]}

    class FakeRunner:
        def ensure_service(self, service, _capabilities):
            return 0, "ready", {}

        def run_workload(self, workload, _capabilities):
            return 0, "warm", {}

        def run_test(self, test, _capabilities):
            container = test.selector["container"]
            if test.driver == "probe.container":
                return 0, str(running[container]).lower(), {}
            application = next(
                name for name in ("nginx", "bind", "postgres")
                if name in test.test_id
            )
            target = {
                "nginx": "app-nginx", "bind": "app-bind",
                "postgres": "app-postgres",
            }[application]
            return (0 if running[target] else 1), "probe", {}

    def fault_runner(command, timeout):
        parts = command.split()
        if "docker stop" in command:
            running[parts[-1]] = False
            return 0, "stopped"
        if "docker start" in command:
            running[parts[-1]] = True
            return 0, "started"
        if "docker inspect" in command:
            return 0, str(running[parts[-1]]).lower()
        return 0, "ok"

    lifecycle = BundleLifecycleExecutor(
        root / "journals", FakeRunner(), fault_runner=fault_runner
    )
    receipts = []
    for index in range(2):
        receipt = root / f"receipt-{index}.json"
        lifecycle.run(first, capabilities, receipt)
        value = json.loads(receipt.read_text())
        assert value["passed"] is True
        assert value["ai_invoked"] is False
        assert value["blind_mode"] is True
        assert value["topology_tainted"] is False
        assert value["convergence"]["passed"] is True
        assert len(value["convergence"]["attempts"]) >= 2
        assert any(
            item.get("phase") == "recovery" for item in value["workloads"]
        )
        receipts.append(receipt)
    qualification = qualify_bundle(
        first, receipts, root / "qualification.json",
        qualification_level="pilot",
    )
    assert json.loads(qualification.read_text())["status"] == "pilot_qualified"

    scale = validate_bundle_scales(first)
    assert scale["passed"] is True
    assert [item["asset_count"] for item in scale["results"]] == [5, 20, 100, 1000, 10000]
    assert scale["results"][-1]["execution_mode"] == "plan_only_no_container_launch"
    real_baseline_scale = validate_bundle_scales(
        first, (5, 20, 100), base_capabilities=pilot_capabilities(18),
    )
    assert [item["asset_count"] for item in real_baseline_scale["results"]] == [18, 20, 100]

    # Coordinator persists leases, exact inputs and output fingerprints.
    coordinator_store = ArtifactStore(root / "coordinator-artifacts")
    tasks = (
        AgentTask(
            task_id="topology_task", agent_role="topology_agent",
            output_artifact_id="coordinator_topology",
            output_artifact_type="topology_ref",
        ),
        AgentTask(
            task_id="service_task", agent_role="service_agent",
            output_artifact_id="coordinator_service",
            output_artifact_type="service", dependencies=("topology_task",),
            input_artifacts=("coordinator_topology",),
        ),
    )
    coordinator = BenchmarkCoordinator(root / "coordinator.json", coordinator_store)
    coordinator.initialize(tasks)
    calls = []

    def topology_handler(task, inputs):
        calls.append(task.task_id)
        assert not inputs
        return AgentArtifact(
            "topology_ref", task.output_artifact_id, task.agent_role,
            {"topology_id": "pilot"}, input_fingerprints=(),
        )

    def service_handler(task, inputs):
        calls.append(task.task_id)
        return AgentArtifact(
            "service", task.output_artifact_id, task.agent_role,
            {"services": []},
            input_fingerprints=tuple(x.artifact_fingerprint for x in inputs),
        )

    state = coordinator.run(
        {"topology_agent": topology_handler, "service_agent": service_handler},
        worker_id="contract_worker",
    )
    assert state["result"] == "complete"
    assert calls == ["topology_task", "service_task"]
    state = coordinator.run({}, worker_id="contract_worker")
    assert state["result"] == "complete" and calls == ["topology_task", "service_task"]

    external_store = ArtifactStore(root / "external-artifacts")
    external = BenchmarkCoordinator(root / "external-state.json", external_store)
    external.initialize((tasks[0],))
    claim = external.claim_next(worker_id="external_agent")
    assert claim["task"]["task_id"] == "topology_task"
    external.complete_claim(
        "topology_task", claim["lease_id"],
        AgentArtifact(
            "topology_ref", "coordinator_topology", "topology_agent",
            {"topology_id": "pilot"}, input_fingerprints=(),
        ),
    )
    assert external.load()["tasks"]["topology_task"]["status"] == "complete"

    # Artifact payload and provenance are protected independently of bundles.
    artifact = store.load("pilot_services")
    changed = artifact.to_dict()
    changed["payload"]["services"] = []
    try:
        AgentArtifact.from_dict(changed)
        raise AssertionError("tampered AgentArtifact was accepted")
    except ValueError as exc:
        assert "fingerprint" in str(exc)


# FaultSpec choose>1 compiles one independently recoverable action per target.
multi_capabilities = pilot_capabilities(10)
multi = FaultSpec(
    fault_id="multi_container_stop", fault_type="container.stopped",
    selector={"role": "Host", "choose": 3}, parameters={},
    expectations={"must_break": ["three_hosts"], "must_preserve": []},
    safety={"max_affected_assets": 3, "max_affected_asns": 3,
            "protected_assets": [], "require_recovery": True},
    seed="multi", schedule={"at_seconds": 0, "duration_seconds": 1},
)
multi_plan = compile_fault(multi, multi_capabilities)
assert len(multi_plan.actions) == 3
assert len(multi_plan.affected_assets) == 3
assert [item.inject_order for item in multi_plan.actions] == [0, 1, 2]
assert [item.cleanup_order for item in multi_plan.actions] == [2, 1, 0]
