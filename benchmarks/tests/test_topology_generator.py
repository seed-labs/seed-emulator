"""Contracts for deterministic, budgeted declarative topology generation."""

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from generator.topology.compiler import build_emulator  # noqa: E402
from generator.topology.bindings import (  # noqa: E402
    bind_fault_component,
    validate_fault_binding,
)
from generator.topology.models import ResourceBudget, TopologyPlan, TopologyRequest  # noqa: E402
from generator.software import (  # noqa: E402
    ManagedFileSpec,
    SoftwareFaultProfile,
    SoftwareSpec,
)
from generator.topology.planner import plan_topology, validate_topology_plan  # noqa: E402
from generator.topology.registry import load_plan, register_request  # noqa: E402
import benchmark_cli  # noqa: E402
import manager  # noqa: E402


request = TopologyRequest(
    topology_id="unit_ring",
    master_seed="unit-seed",
    as_count=4,
    hosts_per_as=2,
    edge_policy="ring",
    extra_links=1,
    budget=ResourceBudget(
        max_containers=32,
        max_networks=32,
        max_memory_mb=8192,
        max_cpu_cores=8,
        max_ases=8,
        max_links=16,
    ),
)
first = plan_topology(request)
second = plan_topology(request)
assert first.to_dict() == second.to_dict()
assert first.topology_name == "DECLARATIVE_unit_ring"
assert len(first.autonomous_systems) == 4
assert len(first.external_links) == 5
assert len({item.asn for item in first.autonomous_systems}) == 4
assert len({item.lan_prefix for item in first.autonomous_systems}) == 4
assert len({item.prefix for item in first.external_links}) == 5
assert first.resource_estimate.containers == 14
assert first.resource_estimate.memory_mb == 1024
assert first.autonomous_systems[0].router_address == "10.0.0.2"
assert first.autonomous_systems[0].host_addresses[0] == "10.0.0.3"
assert first.autonomous_systems[0].loopback_address == "100.64.0.1"
assert first.external_links[0].left_address.endswith(".2")
assert first.external_links[0].right_address.endswith(".3")
validate_topology_plan(first)

round_trip = TopologyPlan.from_dict(json.loads(json.dumps(first.to_dict())))
assert round_trip.to_dict() == first.to_dict()

# SoftwareSpec is additive, deterministic and remains absent from legacy plan
# fingerprints when no software is declared.
software = SoftwareSpec(
    software_id="jq_tools",
    packages=("jq",),
    target_roles=("host",),
    target_asns=(64512,),
    target_nodes=("host0",),
    capabilities=("json.query.v1",),
    managed_files=(
        ManagedFileSpec(
            path="/etc/jq/benchmark.conf", content="mode=healthy\n", mode="0644"
        ),
    ),
    fault_profiles=(
        SoftwareFaultProfile(
            profile_id="wrong_mode",
            fault_type="software.config.replace",
            parameters={
                "path": "/etc/jq/benchmark.conf",
                "healthy_value": "mode=healthy",
                "faulty_value": "mode=broken",
            },
        ),
        SoftwareFaultProfile(
            profile_id="disable_binary",
            fault_type="software.executable.disabled",
            parameters={"path": "/usr/bin/jq", "expected_mode": "0755"},
        ),
    ),
)
software_plan = plan_topology(replace(request, software=(software,)))
software_round_trip = TopologyPlan.from_dict(
    json.loads(json.dumps(software_plan.to_dict()))
)
assert software_round_trip.to_dict() == software_plan.to_dict()
assert software_plan.request["software"][0]["software_id"] == "jq_tools"
assert "software" not in first.request
assert build_emulator(software_plan) is not None

try:
    plan_topology(replace(request, software=(replace(software, packages=("jq;id",)),)))
    raise AssertionError("unsafe apt package declaration was accepted")
except ValueError as exc:
    assert "package" in str(exc)

try:
    invalid_file = replace(
        software,
        managed_files=(ManagedFileSpec(path="/etc/passwd", content="x"),),
        fault_profiles=(),
    )
    plan_topology(replace(request, software=(invalid_file,)))
    raise AssertionError("protected managed file was accepted")
except ValueError as exc:
    assert "file" in str(exc)

try:
    unmatched = replace(
        software, target_roles=("router",), target_nodes=("host0",)
    )
    plan_topology(replace(request, software=(unmatched,)))
    raise AssertionError("software selector matching no assets was accepted")
except ValueError as exc:
    assert "matches no" in str(exc)

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    registered = register_request(request, root=root)
    assert load_plan(request.topology_id, root).to_dict() == registered.to_dict()
    try:
        register_request(request, root=root)
        raise AssertionError("topology overwrite did not require force")
    except FileExistsError:
        pass

try:
    plan_topology(
        replace(
            request,
            budget=replace(request.budget, max_containers=5),
        )
    )
    raise AssertionError("container budget overrun was accepted")
except ValueError as exc:
    assert "budget" in str(exc)

try:
    plan_topology(replace(request, lan_pool="172.16.0.0/16"))
    raise AssertionError("overlapping address pools were accepted")
except ValueError as exc:
    assert "overlap" in str(exc)

try:
    plan_topology(replace(request, loopback_pool="10.0.0.0/16"))
    raise AssertionError("overlapping loopback and LAN pools were accepted")
except ValueError as exc:
    assert "overlap" in str(exc)

try:
    plan_topology(replace(request, ix_prefixlen=30))
    raise AssertionError("IX subnet without a Docker gateway reservation was accepted")
except ValueError as exc:
    assert "Docker gateway" in str(exc)

try:
    plan_topology(replace(request, edge_policy="mesh", budget=replace(request.budget, max_links=3)))
    raise AssertionError("link budget overrun was accepted")
except ValueError as exc:
    assert "link" in str(exc) or "budget" in str(exc)

explicit = plan_topology(
    replace(
        request,
        edge_policy="explicit",
        explicit_edges=((0, 1), (1, 2), (2, 3)),
        extra_links=0,
    )
)
assert len(explicit.external_links) == 3
try:
    plan_topology(
        replace(
            request,
            edge_policy="explicit",
            explicit_edges=((0, 1), (2, 3)),
            extra_links=0,
        )
    )
    raise AssertionError("disconnected explicit graph was accepted")
except ValueError as exc:
    assert "disconnected" in str(exc)

# The adapter must accept the validated plan without touching Docker or output.
emulator = build_emulator(first)
assert emulator is not None

fake_manifest = {
    "assets": [
        {
            "container": "as64512brd-router0-10.0.0.1",
            "asn": 64512,
            "role": "BorderRouter",
            "interfaces": [
                {"name": "lan0", "address": "10.0.0.1/24"},
                {"name": "ix1000", "address": "172.16.0.1/29"},
            ],
        },
        {
            "container": "as64513brd-router0-10.0.1.1",
            "asn": 64513,
            "role": "BorderRouter",
            "interfaces": [
                {"name": "lan0", "address": "10.0.1.1/24"},
                {"name": "ix1000", "address": "172.16.0.2/29"},
            ],
        },
        {
            "container": "as64512h-host0-10.0.0.2",
            "asn": 64512,
            "role": "Host",
            "interfaces": [{"name": "lan0", "address": "10.0.0.2/24"}],
        },
    ],
    "fault_component_bindings": {
        "container_stopped": ["as64512h-host0-10.0.0.2"],
        "dns_nameserver": ["as64512h-host0-10.0.0.2"],
        "bird_wrong_asn": [
            {"container": "as64512brd-router0-10.0.0.1", "correct_asn": 64512}
        ],
        "scoped_acl": [
            {
                "container": "as64512brd-router0-10.0.0.1",
                "asn": 64512,
                "interfaces": [{"name": "ix1000", "address": "172.16.0.1/29"}],
            }
        ],
        "netem": [
            {"container": "as64512h-host0-10.0.0.2", "asn": 64512,
             "interface": "lan0"}
        ],
    },
}
assert bind_fault_component(fake_manifest, "container_stopped", 0, "x") == {
    "container": "as64512h-host0-10.0.0.2"
}
validate_fault_binding(
    fake_manifest,
    "container_stopped",
    {"container": "as64512h-host0-10.0.0.2"},
)
dns = bind_fault_component(fake_manifest, "dns_nameserver", 0, "x")
assert dns["peer_ip"] == "10.0.0.1"
validate_fault_binding(fake_manifest, "dns_nameserver", dns)
bird = bind_fault_component(fake_manifest, "bird_wrong_asn", 0, "x")
assert bird["correct_asn"] == 64512 and bird["bad_asn"] != 64512
validate_fault_binding(fake_manifest, "bird_wrong_asn", bird)
acl = bind_fault_component(fake_manifest, "scoped_acl", 0, "x")
assert acl["source_interface"] == "ix1000"
assert acl["destination_ip"] == "172.16.0.2"
validate_fault_binding(fake_manifest, "scoped_acl", acl)
netem = bind_fault_component(fake_manifest, "netem", 3, "x")
assert netem["container"] == "as64512h-host0-10.0.0.2"
assert netem["interface"] == "lan0"
assert netem["delay_ms"] == 80 and netem["jitter_ms"] == 30
validate_fault_binding(fake_manifest, "netem", netem)
compound = bind_fault_component(
    fake_manifest, "bird_wrong_asn_scoped_acl", 0, "x"
)
assert compound["source_router"] == acl["source_router"]
assert compound["correct_asn"] == compound["source_asn"]
assert compound["peer_protocol"] == f"x_as{compound['destination_asn']}"
validate_fault_binding(fake_manifest, "bird_wrong_asn_scoped_acl", compound)
try:
    validate_fault_binding(
        fake_manifest,
        "container_stopped",
        {"container": "outside-topology"},
    )
    raise AssertionError("out-of-capability mutation target was accepted")
except ValueError as exc:
    assert "outside topology" in str(exc)

# Planning remains cheap at large scale and proves admission-control arithmetic
# without launching any containers. 50 ASes x (1 router + 199 hosts) = 10,000
# business containers; two SEED image-dependency helpers are budgeted too.
large = plan_topology(
    TopologyRequest(
        topology_id="unit_10k",
        master_seed="unit-scale-seed",
        as_count=50,
        hosts_per_as=199,
        edge_policy="ring",
        budget=ResourceBudget(
            max_containers=10002,
            max_networks=128,
            max_memory_mb=2_000_000,
            max_cpu_cores=2000,
            max_ases=64,
            max_links=64,
        ),
    )
)
assert large.resource_estimate.containers == 10002
assert len(large.autonomous_systems) == 50
assert sum(len(item.host_addresses) + 1 for item in large.autonomous_systems) == 10000
assert len(large.external_links) == 50
validate_topology_plan(large)

declarative_name = "DECLARATIVE_small_ring"
assert "generator.topology.cli compile" in benchmark_cli.get_topology_build_cmd(
    declarative_name
)
assert benchmark_cli.get_topology_path(declarative_name).endswith(
    "generated/declarative/small_ring/output"
)
assert benchmark_cli.get_topology_compose_command(declarative_name) == [
    "docker", "compose", "-p", "decl_small_ring"
]
manager_calls = []
original_run = manager.run
original_sleep = manager.time.sleep
try:
    manager.run = lambda command, timeout=180: manager_calls.append((command, timeout))
    manager.time.sleep = lambda _seconds: None
    manager.build_topology(declarative_name)
    manager.start_topology(declarative_name)
finally:
    manager.run = original_run
    manager.time.sleep = original_sleep
assert "generator.topology.cli compile --topology-id small_ring" in manager_calls[0][0]
assert "docker compose -p decl_small_ring up -d" in manager_calls[1][0]
