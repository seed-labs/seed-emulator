#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from seedemu.testing import ComposeRuntimeTest


BACKEND_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_bgp_backend"


def check_backend_config(test: ComposeRuntimeTest, service) -> None:
    if not service:
        return

    backend = str(service.labels.get(BACKEND_LABEL, ""))
    test.structural_check(
        "{} has a recorded BGP backend".format(service.name),
        backend in {"bird", "frr"},
        "unexpected backend label: {}".format(backend),
    )

    if backend == "bird":
        test.exec_check(
            "{} renders BIRD BGP config".format(service.name),
            service,
            "test -f /etc/bird/bird.conf && grep -q 'protocol bgp' /etc/bird/bird.conf",
        )
    if backend == "frr":
        test.exec_check(
            "{} renders FRR BGP config".format(service.name),
            service,
            "test -f /etc/frr/frr.conf && grep -q 'router bgp' /etc/frr/frr.conf",
        )


def check_reachability(test: ComposeRuntimeTest, left_asn: int, right_asn: int) -> None:
    left = test.require_service(left_asn, "host_0", "AS{} host is generated".format(left_asn))
    right = test.require_service(right_asn, "host_0", "AS{} host is generated".format(right_asn))
    if left and right:
        test.exec_check(
            "AS{} reaches AS{} through generated transit AS".format(left_asn, right_asn),
            left,
            "ping -c 3 {} >/dev/null".format(right.address),
            retries=30,
            interval=5,
        )


def load_topology(test: ComposeRuntimeTest):
    topology_path = Path(test.example_dir) / "output" / "topology.json"
    test.structural_check(
        "topology.json is generated",
        topology_path.exists(),
        "missing {}".format(topology_path),
    )
    if not topology_path.exists():
        return None

    with open(topology_path, "r", encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    topology = load_topology(test)

    router_names = []
    if topology:
        router_names = sorted(topology["ebgp_routers"] + topology["internal_routers"])
        routing = topology.get("internal_routing", {})
        test.structural_check(
            "default iBGP mode is full mesh",
            routing.get("mode") == "full-mesh",
            "found {}".format(routing.get("mode")),
        )
        test.structural_check(
            "default BGP scope is all routers",
            routing.get("scope") == "all-routers",
            "found {}".format(routing.get("scope")),
        )

    services = []
    for router_name in router_names:
        service = test.require_service(10, router_name, "AS10 router {} is generated".format(router_name))
        if service:
            services.append(service)
            check_backend_config(test, service)

    bird_count = sum(1 for service in services if str(service.labels.get(BACKEND_LABEL, "")) == "bird")
    frr_count = sum(1 for service in services if str(service.labels.get(BACKEND_LABEL, "")) == "frr")
    test.structural_check(
        "generated routers use both BIRD and FRR",
        bird_count > 0 and frr_count > 0,
        "BIRD count {}, FRR count {}".format(bird_count, frr_count),
    )
    test.structural_check(
        "backend split is approximately balanced",
        abs(bird_count - frr_count) <= 1,
        "BIRD count {}, FRR count {}".format(bird_count, frr_count),
    )

    if topology:
        assignments = topology.get("stub_assignments", {})
        discovered_stubs = sorted(
            int(asn)
            for stub_asns in assignments.values()
            for asn in stub_asns
        )
        test.structural_check(
            "default creates two stub ASes per IX",
            len(discovered_stubs) == 8,
            "found {}".format(discovered_stubs),
        )

    check_reachability(test, 170, 177)
    check_reachability(test, 171, 174)
    check_reachability(test, 176, 173)

    test.write_summary("complex-generated-routing-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
