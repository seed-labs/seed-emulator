"""Contract tests for capability-bound formal Bundle fault profiles."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator.bundle.coordinator import AgentTask  # noqa: E402
from generator.bundle.plugins import builtin_registry  # noqa: E402
from generator.bundle.request import BenchmarkRequest  # noqa: E402
from generator.bundle.workers import (  # noqa: E402
    FaultAgentWorker, TestAgentWorker, WorkerContext,
)
from generator.faults.compiler import compile_fault_set  # noqa: E402
from generator.faults.drivers import DRIVERS  # noqa: E402
from generator.faults.models import FaultSpec  # noqa: E402


def asset(container, asn, role, address, software=(), extra_interfaces=()):
    return {
        "container": container, "asn": asn, "role": role,
        "interfaces": [
            {"name": "lan0", "address": address}, *extra_interfaces,
        ],
        "software": list(software),
    }


bind9 = {
    "software_id": "bind9", "capabilities": ["dns.bind9.v1"],
    "packages": ["bind9", "dnsutils"], "fault_profiles": [],
}
observer_software = {
    "software_id": "curl_tools", "capabilities": ["observer.network.v1"],
    "packages": ["curl", "dnsutils"], "fault_profiles": [],
}
iptables = {
    "software_id": "iptables", "capabilities": ["firewall.iptables.v1"],
    "packages": ["iptables"], "fault_profiles": [],
}
jq_tools = {
    "software_id": "jq_tools", "capabilities": ["json.query.v1"],
    "packages": ["jq"], "managed_files": [
        {"path": "/etc/jq/benchmark.conf", "mode": "0644"},
    ],
    "fault_profiles": [
        {"profile_id": "wrong_mode", "fault_type": "software.config.replace",
         "parameters": {"path": "/etc/jq/benchmark.conf",
                        "healthy_value": "mode=healthy", "faulty_value": "mode=broken"}},
        {"profile_id": "disable_binary", "fault_type": "software.executable.disabled",
         "parameters": {"path": "/usr/bin/jq", "expected_mode": "0755"}},
    ],
}
assets = [
    asset("router-a", 64512, "BorderRouter", "10.0.0.2/24", (iptables,),
          ({"name": "ix1000", "address": "172.16.0.2/24"},)),
    asset("router-b", 64513, "BorderRouter", "10.0.1.2/24", (iptables,),
          ({"name": "ix1000", "address": "172.16.0.3/24"},)),
    asset("app-bind", 64512, "Host", "10.0.0.3/24", (bind9,)),
    asset("peer-host", 64512, "Host", "10.0.0.4/24", (jq_tools,)),
    asset("observer", 64513, "Host", "10.0.1.4/24", (observer_software,)),
]
manifest = {
    "schema_version": 1,
    "topology_id": "bundle_fault_profile_test",
    "topology_fingerprint": "b" * 64,
    "compose_project": "decl_bundle_fault_profile_test",
    "assets": assets,
    "software_catalog": [bind9, observer_software, iptables, jq_tools],
    "fault_component_bindings": {
        "container_stopped": ["app-bind", "peer-host", "observer"],
        "dns_nameserver": ["app-bind", "observer"],
        "bird_wrong_asn": [
            {"container": "router-a", "correct_asn": 64512},
            {"container": "router-b", "correct_asn": 64513},
        ],
        "scoped_acl": [
            {"container": "router-a", "asn": 64512,
             "interfaces": [{"name": "ix1000", "address": "172.16.0.2/24"}]},
            {"container": "router-b", "asn": 64513,
             "interfaces": [{"name": "ix1000", "address": "172.16.0.3/24"}]},
        ],
        "netem": [
            {"container": item["container"], "asn": item["asn"], "interface": "lan0"}
            for item in assets
        ],
        "ipv6_connected_route": [
            {"container": "router-a", "interface": "benchmark6",
             "address": "2001:db8:0::1/64", "prefix": "2001:db8:0::/64"},
        ],
        "bird_ospf_wrong_area": [
            {"container": "router-a", "correct_area": 0},
        ],
        "docker_network_disconnected": [
            {"container": "peer-host",
             "docker_network": "decl_bundle_fault_profile_test_net_64512_lan0",
             "interface": "lan0", "target_ip": "10.0.0.4",
             "peer_container": "router-a", "peer_ip": "10.0.0.2",
             "remove_interface": False, "bird_reconfigure": False},
        ],
        "software_fault_profiles": [
            {"container": "peer-host", "software_id": "jq_tools",
             "profile_id": profile["profile_id"], "fault_type": profile["fault_type"],
             "parameters": dict(profile["parameters"])}
            for profile in jq_tools["fault_profiles"]
        ],
    },
}


def task(role, artifact_type):
    return AgentTask(
        task_id=f"test_{role}", agent_role=role,
        output_artifact_id=f"test_{artifact_type}",
        output_artifact_type=artifact_type,
    )


expected_probes = {
    "dns.nameserver": "probe.hostname",
    "routing.bird.wrong_asn": "probe.file",
    "network.acl.scoped": "probe.icmp",
    "network.ipv6.connected_route_removed": "probe.ipv6_route",
    "routing.bird.ospf_wrong_area": "probe.file",
    "docker.network.disconnected": "probe.docker_network_path",
    "software.config.replace": "probe.file",
    "software.executable.disabled": "probe.executable",
}
for fault_type in (
    "container.stopped", "dns.nameserver", "routing.bird.wrong_asn",
    "network.acl.scoped", "network.netem",
    "network.ipv6.connected_route_removed", "routing.bird.ospf_wrong_area",
    "docker.network.disconnected", "software.config.replace",
    "software.executable.disabled",
):
    request = BenchmarkRequest.from_dict({
        "schema_version": 1,
        "request_id": f"test_{fault_type.replace('.', '_')}",
        "objective": "formal fault profile contract",
        "topology_id": manifest["topology_id"],
        "applications": ["bind9"],
        "fault_types": [fault_type],
        "fault_count": 1,
        "seed": "bundle-profile-v1",
    })
    context = WorkerContext.build(request, manifest)
    fault_payload = FaultAgentWorker(context)(
        task("fault_agent", "fault_set"), (),
    ).payload
    assert fault_payload["faults"][0]["fault_type"] == fault_type
    assert "observer" not in fault_payload["faults"][0]["selector"].values()
    specs = tuple(FaultSpec.from_dict(item) for item in fault_payload["faults"])
    plan = compile_fault_set(specs, manifest, relationship=fault_payload["relationship"])
    assert len(plan.actions) == 1
    assert plan.actions[0].inject_command and plan.actions[0].cleanup_command

    tests = TestAgentWorker(context)(task("test_agent", "test"), ()).payload["tests"]
    active = {item["expectation_id"] for item in tests if item["phase"] == "active"}
    recovery = {item["expectation_id"] for item in tests if item["phase"] == "recovery"}
    must_break = set(fault_payload["faults"][0]["expectations"]["must_break"])
    assert must_break <= active, (fault_type, must_break, active)
    assert must_break <= recovery, (fault_type, must_break, recovery)
    if fault_type in expected_probes:
        assert expected_probes[fault_type] in {item["driver"] for item in tests}
    if fault_type == "network.netem":
        assert fault_payload["faults"][0]["parameters"]["loss_percent"] == 100

registry = builtin_registry(DRIVERS)
registry.require("probe.hostname", kind="probe")
registry.require("probe.icmp", kind="probe")
registry.require("probe.docker_network_path", kind="probe")

# One application can carry a conflict-checked cascading fault set. The
# compiler preserves dependency order and always recovers in reverse order.
compound_request = BenchmarkRequest.from_dict({
    "schema_version": 1, "request_id": "test_cascading_compound",
    "objective": "generic cascading composition",
    "topology_id": manifest["topology_id"], "applications": ["bind9"],
    "fault_types": [
        "dns.nameserver", "routing.bird.ospf_wrong_area",
        "software.config.replace",
    ],
    "fault_count": 3, "fault_relationship": "cascading",
    "seed": "bundle-compound-v1",
})
compound_context = WorkerContext.build(compound_request, manifest)
compound_payload = FaultAgentWorker(compound_context)(
    task("fault_agent", "fault_set"), (),
).payload
compound_specs = tuple(
    FaultSpec.from_dict(item) for item in compound_payload["faults"]
)
assert compound_payload["relationship"] == "cascading"
assert not compound_specs[0].depends_on
assert compound_specs[1].depends_on == (compound_specs[0].fault_id,)
assert compound_specs[2].depends_on == (compound_specs[1].fault_id,)
compound_plan = compile_fault_set(
    compound_specs, manifest, relationship="cascading"
)
assert compound_plan.impact["dependency_edges"]
assert compound_plan.impact["recovery_order"] == list(reversed(
    compound_plan.impact["injection_order"]
))

try:
    bad = BenchmarkRequest.from_dict({
        "schema_version": 1, "request_id": "test_unprofiled_fault",
        "objective": "fail closed", "topology_id": manifest["topology_id"],
        "applications": ["bind9"], "fault_types": ["routing.frr.route_map"],
        "fault_count": 1, "seed": "bundle-profile-v1",
    })
    FaultAgentWorker(WorkerContext.build(bad, manifest))(
        task("fault_agent", "fault_set"), (),
    )
    raise AssertionError("unprofiled Bundle fault was accepted")
except ValueError as exc:
    assert "formal Bundle profile" in str(exc) or "formal Bundle profiles" in str(exc)

print("bundle fault profile tests passed")
