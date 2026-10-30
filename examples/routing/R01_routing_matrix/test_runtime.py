#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


BACKEND_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_bgp_backend"
BGP_ROLE_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_bgp_role"


def require_router(test: ComposeRuntimeTest, asn: int, name: str):
    return test.require_service(asn, name, "AS{} router {} is generated".format(asn, name))


def check_backend_label(test: ComposeRuntimeTest, service, expected: str) -> None:
    if not service:
        return
    actual = str(service.labels.get(BACKEND_LABEL, ""))
    test.structural_check(
        "{} uses {} backend".format(service.name, expected),
        actual == expected,
        "expected {}, found {}".format(expected, actual),
    )


def check_bird_router(test: ComposeRuntimeTest, service, description: str) -> None:
    if not service:
        return
    check_backend_label(test, service, "bird")
    test.exec_check(
        "{} has BIRD BGP config".format(description),
        service,
        "test -f /etc/bird/bird.conf && grep -q 'protocol bgp' /etc/bird/bird.conf",
    )


def check_frr_router(test: ComposeRuntimeTest, service, description: str) -> None:
    if not service:
        return
    check_backend_label(test, service, "frr")
    test.exec_check(
        "{} has FRR BGP config".format(description),
        service,
        "test -f /etc/frr/frr.conf && grep -q 'router bgp' /etc/frr/frr.conf",
    )


def check_reachability(test: ComposeRuntimeTest, left_asn: int, right_asn: int, description: str) -> None:
    left = test.require_service(left_asn, "host_0", "AS{} host is generated".format(left_asn))
    right = test.require_service(right_asn, "host_0", "AS{} host is generated".format(right_asn))
    if left and right:
        test.exec_check(
            description,
            left,
            "ping -c 3 {} >/dev/null".format(right.address),
            retries=30,
            interval=5,
        )


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    # AS2: all-router full mesh, BIRD.
    as2_edge0 = require_router(test, 2, "edge0")
    as2_core0 = require_router(test, 2, "core0")
    as2_core1 = require_router(test, 2, "core1")
    as2_edge1 = require_router(test, 2, "edge1")
    for service, name in [
        (as2_edge0, "AS2 edge0"),
        (as2_core0, "AS2 core0"),
        (as2_core1, "AS2 core1"),
        (as2_edge1, "AS2 edge1"),
    ]:
        check_bird_router(test, service, name)
    check_reachability(test, 150, 151, "AS150 reaches AS151 through AS2 BIRD full mesh")

    # AS3: all-router full mesh, FRR.
    as3_edge0 = require_router(test, 3, "edge0")
    as3_core0 = require_router(test, 3, "core0")
    as3_core1 = require_router(test, 3, "core1")
    as3_edge1 = require_router(test, 3, "edge1")
    for service, name in [
        (as3_edge0, "AS3 edge0"),
        (as3_core0, "AS3 core0"),
        (as3_core1, "AS3 core1"),
        (as3_edge1, "AS3 edge1"),
    ]:
        check_frr_router(test, service, name)
    check_reachability(test, 152, 153, "AS152 reaches AS153 through AS3 FRR full mesh")

    # AS4: BIRD route reflector.
    as4_core0 = require_router(test, 4, "core0")
    check_bird_router(test, as4_core0, "AS4 core0 RR")
    if as4_core0:
        test.exec_check(
            "AS4 BIRD RR renders cluster/client config",
            as4_core0,
            "grep -q 'rr client' /etc/bird/bird.conf && grep -q 'rr cluster id 10.4.0.1' /etc/bird/bird.conf",
        )
    check_reachability(test, 154, 155, "AS154 reaches AS155 through AS4 BIRD RR")

    # AS5: FRR route reflector.
    as5_core0 = require_router(test, 5, "core0")
    check_frr_router(test, as5_core0, "AS5 core0 RR")
    if as5_core0:
        test.exec_check(
            "AS5 FRR RR renders cluster/client config",
            as5_core0,
            "grep -q 'bgp cluster-id 10.5.0.1' /etc/frr/frr.conf && grep -q 'route-reflector-client' /etc/frr/frr.conf",
        )
    check_reachability(test, 156, 157, "AS156 reaches AS157 through AS5 FRR RR")

    # AS6: auto-completed RR with mixed backend. The deterministic RR is core0.
    as6_core0 = require_router(test, 6, "core0")
    as6_core1 = require_router(test, 6, "core1")
    check_frr_router(test, as6_core0, "AS6 auto RR core0")
    check_bird_router(test, as6_core1, "AS6 auto RR core1")
    if as6_core0:
        test.exec_check(
            "AS6 auto RR uses deterministic default cluster",
            as6_core0,
            "grep -q 'bgp cluster-id 10.6.0.1' /etc/frr/frr.conf && grep -q 'route-reflector-client' /etc/frr/frr.conf",
        )
    check_reachability(test, 158, 159, "AS158 reaches AS159 through AS6 auto RR")

    # AS7: edge-only full mesh. It is a structural BGP-free-core control-plane
    # test; plain-IP end-to-end reachability is intentionally not required.
    as7_edge0 = require_router(test, 7, "edge0")
    as7_edge1 = require_router(test, 7, "edge1")
    as7_core0 = require_router(test, 7, "core0")
    as7_core1 = require_router(test, 7, "core1")
    for service, expected in [(as7_edge0, "edge"), (as7_edge1, "edge"), (as7_core0, "core"), (as7_core1, "core")]:
        if service:
            actual = str(service.labels.get(BGP_ROLE_LABEL, ""))
            test.structural_check(
                "{} has BGP role {}".format(service.name, expected),
                actual == expected,
                "expected {}, found {}".format(expected, actual),
            )
    if as7_edge0:
        test.exec_check(
            "AS7 edge0 has iBGP to edge1",
            as7_edge0,
            "grep -Eq 'neighbor .* as 7|remote-as 7' /etc/bird/bird.conf",
        )
    if as7_core0:
        test.exec_check(
            "AS7 core0 does not receive BGP sessions",
            as7_core0,
            "! grep -Eq 'protocol bgp|router bgp' /etc/frr/frr.conf",
        )
    if as7_core1:
        test.exec_check(
            "AS7 core1 does not receive BGP sessions",
            as7_core1,
            "! grep -Eq 'protocol bgp|router bgp' /etc/bird/bird.conf",
        )

    test.write_summary("routing-matrix-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
