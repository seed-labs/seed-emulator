"""Deterministic three-application pilot used by tests and integrators."""

from __future__ import annotations

from pathlib import Path
import ipaddress
from typing import Any, Dict, Mapping, Tuple

from generator.bundle.artifacts import AgentArtifact, ArtifactStore
from generator.bundle.models import BenchmarkBundleSpec


PILOT_FINGERPRINT = "a" * 64


def pilot_capabilities(asset_count: int = 4) -> Dict[str, object]:
    if asset_count < 4:
        raise ValueError("pilot requires at least four assets")
    applications = (
        ("app-nginx", "nginx", "http.nginx.v1"),
        ("app-bind", "bind9", "dns.bind9.v1"),
        ("app-postgres", "postgresql", "database.postgresql.v1"),
        ("observer", "curl_tools", "observer.network.v1"),
    )
    assets = []
    for index in range(asset_count):
        if index < len(applications):
            container, software_id, capability = applications[index]
        else:
            container, software_id, capability = (
                f"scale-host-{index:05d}", "curl_tools", "observer.network.v1"
            )
        assets.append({
            "container": container, "asn": 64512 + index // 200,
            "role": "Host",
            "interfaces": [{
                "name": "lan0",
                "address": f"{ipaddress.ip_address(int(ipaddress.ip_address('10.0.0.0')) + index + 1)}/8",
            }],
            "software": [{
                "software_id": software_id, "capabilities": [capability],
                "packages": [software_id], "fault_profiles": [],
            }],
        })
    return {
        "schema_version": 1,
        "topology_id": "multi_agent_application_pilot",
        "topology_fingerprint": PILOT_FINGERPRINT,
        "assets": assets,
        "software_catalog": [
            {"software_id": item[1], "capabilities": [item[2]]}
            for item in applications
        ],
    }


def _artifact(artifact_type, artifact_id, producer, payload):
    return AgentArtifact(
        artifact_type=artifact_type, artifact_id=artifact_id,
        producer=producer, payload=payload,
    )


def _pilot_bindings(capabilities: Mapping[str, Any]) -> Dict[str, str]:
    by_node = {
        str(item.get("node_name", "")): item
        for item in capabilities.get("assets", ())
        if item.get("role") == "Host"
    }
    if not {"host0", "host1", "host2", "host3"} <= set(by_node):
        # The in-memory contract fixture intentionally has friendly container
        # names and no SEED node_name labels.
        by_container = {
            str(item.get("container")): item
            for item in capabilities.get("assets", ())
        }
        expected = ("app-nginx", "app-bind", "app-postgres", "observer")
        if not all(name in by_container for name in expected):
            raise ValueError("pilot capability manifest lacks four application assets")
        selected = dict(zip(("host0", "host1", "host2", "host3"),
                            (by_container[name] for name in expected)))
    else:
        selected = {name: by_node[name] for name in ("host0", "host1", "host2", "host3")}

    def address(item):
        lan = next(
            (entry for entry in item.get("interfaces", ())
             if entry.get("name") == "lan0"), None
        )
        return str(lan["address"]).split("/")[0] if lan else str(item["container"])

    return {
        "nginx": str(selected["host0"]["container"]),
        "bind": str(selected["host1"]["container"]),
        "postgres": str(selected["host2"]["container"]),
        "observer": str(selected["host3"]["container"]),
        "nginx_address": address(selected["host0"]),
        "bind_address": address(selected["host1"]),
        "postgres_address": address(selected["host2"]),
    }


def write_pilot_artifacts(
    root: Path, capabilities: Mapping[str, Any] | None = None,
) -> Tuple[ArtifactStore, BenchmarkBundleSpec]:
    capabilities = dict(capabilities or pilot_capabilities())
    binding = _pilot_bindings(capabilities)
    real = capabilities.get("topology_fingerprint") != PILOT_FINGERPRINT
    topology_id = str(
        capabilities.get("topology_id", "multi_agent_application_pilot")
    )
    service_parameters = {
        "nginx": {
            "start_argv": ["service", "nginx", "start"],
            "health_argv": ["curl", "-fsS", "http://127.0.0.1/"],
        },
        "bind": {
            "start_argv": ["service", "named", "start"],
            "health_argv": ["rndc", "status"],
        },
        "postgres": {
            "start_argv": ["service", "postgresql", "start"],
            "health_argv": ["pg_isready"],
        },
    } if real else {"nginx": {}, "bind": {}, "postgres": {}}

    probes = {
        "nginx": ("probe.http", {"url": f"http://{binding['nginx_address']}/"}),
        "bind": ("probe.dns", {
            "name": "service.pilot.test", "server": binding["bind_address"],
        }),
        # PostgreSQL listens on loopback by default in the base distribution;
        # run this probe from the service asset while preserving the independent
        # observer as a separate must_preserve assertion.
        "postgres": ("probe.tcp", {"host": "127.0.0.1", "port": 5432}),
    }
    source = {
        "nginx": binding["observer"], "bind": binding["observer"],
        "postgres": binding["postgres"],
    }
    store = ArtifactStore(root)
    artifacts = (
        _artifact("topology_ref", "pilot_topology", "topology_agent", {
            "topology_id": topology_id,
        }),
        _artifact("software", "pilot_software", "software_agent", {
            "required_software": ["nginx", "bind9", "postgresql", "curl_tools"],
        }),
        _artifact("service", "pilot_services", "service_agent", {"services": [
            {"schema_version": 1, "service_id": "nginx_service", "driver": "service.process", "selector": {"container": binding["nginx"]}, "capabilities_required": ["http.nginx.v1"], "ports": [80], "parameters": service_parameters["nginx"]},
            {"schema_version": 1, "service_id": "bind_service", "driver": "service.process", "selector": {"container": binding["bind"]}, "capabilities_required": ["dns.bind9.v1"], "ports": [53], "parameters": service_parameters["bind"]},
            {"schema_version": 1, "service_id": "postgres_service", "driver": "service.process", "selector": {"container": binding["postgres"]}, "capabilities_required": ["database.postgresql.v1"], "ports": [5432], "parameters": service_parameters["postgres"]},
        ]}),
        _artifact("workload", "pilot_workloads", "workload_agent", {"workloads": [
            {"schema_version": 1, "workload_id": "http_load", "driver": "workload.http", "source": {"container": source["nginx"]}, "target_service": "nginx_service", "parameters": {"url": f"http://{binding['nginx_address']}/"}},
            {"schema_version": 1, "workload_id": "dns_load", "driver": "workload.dns", "source": {"container": source["bind"]}, "target_service": "bind_service", "parameters": {"name": "service.pilot.test", "server": binding["bind_address"]}},
            {"schema_version": 1, "workload_id": "postgres_load", "driver": "workload.tcp", "source": {"container": source["postgres"]}, "target_service": "postgres_service", "parameters": {"host": "127.0.0.1", "port": 5432}},
        ]}),
        _artifact("fault_set", "pilot_faults", "fault_agent", {
            "relationship": "independent", "faults": [
                {"schema_version": 1, "fault_id": f"stop_{name}", "fault_type": "container.stopped", "selector": {"container": container}, "parameters": {}, "expectations": {"must_break": [f"{name}_availability"], "must_preserve": ["observer_availability"]}, "safety": {"max_affected_assets": 3, "max_affected_asns": 3, "protected_assets": ["observer"], "require_recovery": True}, "seed": "pilot", "schedule": {"at_seconds": 0}}
                for index, (name, container) in enumerate((
                    ("nginx", binding["nginx"]), ("bind", binding["bind"]),
                    ("postgres", binding["postgres"]),
                ))
            ],
        }),
        _artifact("test", "pilot_tests", "test_agent", {"tests": [
            *[
                {"schema_version": 1, "test_id": f"baseline_{name}", "phase": "baseline", "driver": probes[name][0], "selector": {"container": source[name]}, "parameters": probes[name][1], "assertion": {"kind": "exit_code", "value": 0}, "expectation_id": f"{name}_healthy", "retries": 2}
                for name in ("nginx", "bind", "postgres")
            ],
            {"schema_version": 1, "test_id": "baseline_observer", "phase": "baseline", "driver": "probe.container", "selector": {"container": binding["observer"]}, "parameters": {}, "assertion": {"kind": "equals", "value": "true"}, "expectation_id": "observer_healthy"},
            *[
                {"schema_version": 1, "test_id": f"active_{name}", "phase": "active", "driver": probes[name][0], "selector": {"container": source[name]}, "parameters": probes[name][1], "assertion": {"kind": "exit_code_not", "value": 0}, "expectation_id": f"{name}_availability"}
                for name in ("nginx", "bind", "postgres")
            ],
            {"schema_version": 1, "test_id": "active_observer", "phase": "active", "driver": "probe.container", "selector": {"container": binding["observer"]}, "parameters": {}, "assertion": {"kind": "equals", "value": "true"}, "expectation_id": "observer_availability"},
            *[
                {"schema_version": 1, "test_id": f"recovery_{name}", "phase": "recovery", "driver": probes[name][0], "selector": {"container": source[name]}, "parameters": probes[name][1], "assertion": {"kind": "exit_code", "value": 0}, "expectation_id": f"{name}_availability", "retries": 5}
                for name in ("nginx", "bind", "postgres")
            ],
        ]}),
        _artifact("oracle", "pilot_oracle", "oracle_agent", {"oracles": [{
            "schema_version": 1, "oracle_id": "pilot_oracle_v1",
            "required_tests": ["active_nginx", "active_bind", "active_postgres", "active_observer", "recovery_nginx", "recovery_bind", "recovery_postgres"],
            "phase_requirements": {"active": ["active_nginx", "active_bind", "active_postgres", "active_observer"], "recovery": ["recovery_nginx", "recovery_bind", "recovery_postgres"]},
        }]}),
        _artifact("scoring", "pilot_scoring", "scoring_agent", {"scoring": [{
            "schema_version": 1, "scoring_id": "pilot_weighted", "weights": {
                "active_nginx": 1, "active_bind": 1, "active_postgres": 1,
                "active_observer": 1, "recovery_nginx": 1,
                "recovery_bind": 1, "recovery_postgres": 1,
            }, "pass_threshold": 1.0,
        }]}),
        _artifact("blind_policy", "pilot_blind", "safety_agent", {"policies": [{}]}),
        _artifact("lifecycle", "pilot_lifecycle", "lifecycle_agent", {"lifecycles": [{"repeat_runs": 2}]}),
    )
    for artifact in artifacts:
        store.write(artifact)
    return store, BenchmarkBundleSpec(
        benchmark_id="multi_agent_application_pilot", seed="pilot-seed-v1",
        artifact_ids=tuple(item.artifact_id for item in artifacts), enabled=False,
    )
