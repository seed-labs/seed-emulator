#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


BGP_ROLE_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_bgp_role"


def require_router(test: ComposeRuntimeTest, asn: int, name: str):
    return test.require_service(asn, name, "AS{} router {} is generated".format(asn, name))


def check_reachability(test: ComposeRuntimeTest, left_asn: int, right_asn: int, description: str) -> None:
    left = test.require_service(left_asn, "host_0", "AS{} host is generated".format(left_asn))
    right = test.require_service(right_asn, "host_0", "AS{} host is generated".format(right_asn))
    if left and right:
        test.exec_check(
            description,
            left,
            "ping -c 3 {} >/dev/null".format(right.address),
            retries=40,
            interval=5,
        )


def check_mpls_router(test: ComposeRuntimeTest, service, description: str) -> None:
    if not service:
        return
    test.exec_check(
        "{} has LDP/MPLS FRR config".format(description),
        service,
        "grep -q 'mpls ldp' /etc/frr/frr.conf && grep -q 'router ospf' /etc/frr/frr.conf",
    )


def check_bgp_free_core(test: ComposeRuntimeTest, service, description: str) -> None:
    if not service:
        return
    test.exec_check(
        "{} remains BGP-free".format(description),
        service,
        "! grep -q 'router bgp' /etc/frr/frr.conf",
    )


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    # AS8: edge-only full mesh with MPLS forwarding.
    as8_edge0 = require_router(test, 8, "edge0")
    as8_edge1 = require_router(test, 8, "edge1")
    as8_core0 = require_router(test, 8, "core0")
    as8_core1 = require_router(test, 8, "core1")
    for service, expected in [(as8_edge0, "edge"), (as8_edge1, "edge"), (as8_core0, "core"), (as8_core1, "core")]:
        if service:
            actual = str(service.labels.get(BGP_ROLE_LABEL, ""))
            test.structural_check(
                "{} has BGP role {}".format(service.name, expected),
                actual == expected,
                "expected {}, found {}".format(expected, actual),
            )
            check_mpls_router(test, service, service.name)
    check_bgp_free_core(test, as8_core0, "AS8 core0")
    check_bgp_free_core(test, as8_core1, "AS8 core1")
    check_reachability(test, 162, 163, "AS162 reaches AS163 through AS8 MPLS BGP-free core")

    # AS9: edge-only route reflector with MPLS forwarding.
    as9_edge0 = require_router(test, 9, "edge0")
    as9_edge1 = require_router(test, 9, "edge1")
    as9_core0 = require_router(test, 9, "core0")
    as9_core1 = require_router(test, 9, "core1")
    for service, expected in [(as9_edge0, "edge"), (as9_edge1, "edge"), (as9_core0, "core"), (as9_core1, "core")]:
        if service:
            actual = str(service.labels.get(BGP_ROLE_LABEL, ""))
            test.structural_check(
                "{} has BGP role {}".format(service.name, expected),
                actual == expected,
                "expected {}, found {}".format(expected, actual),
            )
            check_mpls_router(test, service, service.name)
    if as9_edge0:
        test.exec_check(
            "AS9 edge0 route reflector renders FRR RR config",
            as9_edge0,
            "grep -q 'bgp cluster-id 10.9.0.1' /etc/frr/frr.conf && grep -q 'route-reflector-client' /etc/frr/frr.conf",
        )
    check_bgp_free_core(test, as9_core0, "AS9 core0")
    check_bgp_free_core(test, as9_core1, "AS9 core1")
    check_reachability(test, 164, 165, "AS164 reaches AS165 through AS9 MPLS RR BGP-free core")

    test.write_summary("bgp-free-core-mpls-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
