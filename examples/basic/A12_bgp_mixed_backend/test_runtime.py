#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest, ComposeService


ROUTING_BACKEND_LABEL = "org.seedsecuritylabs.seedemu.meta.seedemu_routing_backend"
ASN_LABEL = "org.seedsecuritylabs.seedemu.meta.asn"
NODE_LABEL = "org.seedsecuritylabs.seedemu.meta.nodename"


def require_backend(test: ComposeRuntimeTest, service: ComposeService, backend: str) -> None:
    actual = service.labels.get(ROUTING_BACKEND_LABEL)
    label = "AS{} {} uses {} routing backend".format(
        service.labels.get(ASN_LABEL),
        service.labels.get(NODE_LABEL),
        backend,
    )
    test.structural_check(
        label,
        actual == backend,
        "expected {}, found {}".format(backend, actual),
    )


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    as2_r1 = test.require_service(2, "r1")
    as2_r2 = test.require_service(2, "r2")
    as151_router = test.require_service(151, "router0")
    as152_router = test.require_service(152, "router0")

    if as2_r1:
        require_backend(test, as2_r1, "bird")
        test.exec_check("AS2 r1 starts BIRD", as2_r1, "pgrep -x bird >/dev/null")
        test.exec_check("AS2 r1 has BIRD BGP intent", as2_r1, "grep -q 'neighbor 10.100.0.151 as 151' /etc/bird/bird.conf")
        test.exec_check("AS2 r1 iBGP session is established", as2_r1, "birdc show protocols | grep -q 'ibgp1.*Established'")
        test.exec_check("AS2 r1 learns AS152 route", as2_r1, "birdc show route | grep -q '10.152.0.0/24'")
        test.exec_check("AS2 r1 does not carry FRR config", as2_r1, "test ! -e /etc/frr/frr.conf")

    if as2_r2:
        require_backend(test, as2_r2, "frr")
        test.exec_check("AS2 r2 starts FRR bgpd", as2_r2, "pgrep -x bgpd >/dev/null")
        test.exec_check("AS2 r2 renders FRR BGP", as2_r2, "grep -q 'router bgp 2' /etc/frr/frr.conf")
        test.exec_check("AS2 r2 renders FRR OSPF", as2_r2, "grep -q 'router ospf' /etc/frr/frr.conf")
        test.exec_check(
            "AS2 r2 learns AS151 route through iBGP from r1",
            as2_r2,
            "vtysh -c 'show ip bgp 10.151.0.0/24' | grep -q '10.0.0.1'",
        )
        test.exec_check("AS2 r2 learns AS151 route", as2_r2, "vtysh -c 'show ip bgp' | grep -q '10.151.0.0/24'")
        test.exec_check("AS2 r2 does not start BIRD", as2_r2, "! pgrep -x bird >/dev/null")

    if as151_router:
        require_backend(test, as151_router, "frr")
        test.exec_check("AS151 router starts FRR bgpd", as151_router, "pgrep -x bgpd >/dev/null")
        test.exec_check(
            "AS151 FRR router has AS2 peer",
            as151_router,
            "grep -q 'neighbor 10.100.0.2 remote-as 2' /etc/frr/frr.conf",
        )
        test.exec_check(
            "AS151 FRR router learns AS152 route",
            as151_router,
            "vtysh -c 'show ip bgp' | grep -q '10.152.0.0/24'",
        )

    if as152_router:
        require_backend(test, as152_router, "bird")
        test.exec_check("AS152 router starts BIRD", as152_router, "pgrep -x bird >/dev/null")
        test.exec_check("AS152 BIRD router has AS2 peer", as152_router, "grep -q 'neighbor 10.101.0.2 as 2' /etc/bird/bird.conf")
        test.exec_check("AS152 BIRD router learns AS151 route", as152_router, "birdc show route | grep -q '10.151.0.0/24'")

    test.write_summary("a12-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
