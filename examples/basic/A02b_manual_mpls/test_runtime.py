#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    web151 = test.require_service(151, "web")
    web152 = test.require_service(152, "web")
    web153 = test.require_service(153, "web")
    e1 = test.require_service(2, "e1")
    e2 = test.require_service(2, "e2")
    e3 = test.require_service(2, "e3")
    r1 = test.require_service(2, "r1")
    r2 = test.require_service(2, "r2")
    r3 = test.require_service(2, "r3")

    if web151 and web152:
        test.exec_check("AS151 fetches AS152 web service", web151, "curl -fsS http://{} >/dev/null".format(web152.address))
        test.exec_check("AS152 reaches AS151 by ICMP", web152, "ping -c 3 {} >/dev/null".format(web151.address))
    if web151 and web153:
        test.exec_check("AS151 fetches AS153 web service", web151, "curl -fsS http://{} >/dev/null".format(web153.address))
        test.exec_check("AS153 reaches AS151 by ICMP", web153, "ping -c 3 {} >/dev/null".format(web151.address))

    if e1:
        test.exec_check(
            "e1 pushes labels toward the core and pops labels for AS151",
            e1,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 200' /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 210' /manual_mpls_setup.sh && "
            "grep -q 'route replace 302 via inet 10.101.0.151 dev ix101' /manual_mpls_setup.sh && "
            "grep -q 'route replace 402 via inet 10.101.0.151 dev ix101' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )
    if e2:
        test.exec_check(
            "e2 pushes labels toward the core and pops labels for AS152",
            e2,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 300' /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 310' /manual_mpls_setup.sh && "
            "grep -q 'route replace 202 via inet 10.102.0.152 dev ix102' /manual_mpls_setup.sh && "
            "grep -q 'route replace 412 via inet 10.102.0.152 dev ix102' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )
    if e3:
        test.exec_check(
            "e3 pushes labels toward the core and pops labels for AS153",
            e3,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 400' /manual_mpls_setup.sh && "
            "grep -q 'encap mpls 410' /manual_mpls_setup.sh && "
            "grep -q 'route replace 212 via inet 10.103.0.153 dev ix103' /manual_mpls_setup.sh && "
            "grep -q 'route replace 312 via inet 10.103.0.153 dev ix103' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )

    if r1:
        test.exec_check(
            "r1 swaps labels between e1 and the core triangle",
            r1,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'route replace 200 as 201' /manual_mpls_setup.sh && "
            "grep -q 'route replace 210 as 211' /manual_mpls_setup.sh && "
            "grep -q 'route replace 301 as 302' /manual_mpls_setup.sh && "
            "grep -q 'route replace 401 as 402' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )
    if r2:
        test.exec_check(
            "r2 swaps labels between e2 and the core triangle",
            r2,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'route replace 201 as 202' /manual_mpls_setup.sh && "
            "grep -q 'route replace 300 as 301' /manual_mpls_setup.sh && "
            "grep -q 'route replace 310 as 311' /manual_mpls_setup.sh && "
            "grep -q 'route replace 411 as 412' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )
    if r3:
        test.exec_check(
            "r3 swaps labels between e3 and the core triangle",
            r3,
            "test -x /manual_mpls_setup.sh && "
            "grep -q 'route replace 211 as 212' /manual_mpls_setup.sh && "
            "grep -q 'route replace 311 as 312' /manual_mpls_setup.sh && "
            "grep -q 'route replace 400 as 401' /manual_mpls_setup.sh && "
            "grep -q 'route replace 410 as 411' /manual_mpls_setup.sh && "
            "test -s /manual_mpls_table.txt && test ! -e /mpls_ifaces.txt",
        )

    for router in (e1, e2, e3, r1, r2, r3):
        if router:
            test.exec_check(
                "{} does not use LDP".format(router.name),
                router,
                "test ! -e /etc/frr/frr.conf || ! grep -q 'mpls ldp' /etc/frr/frr.conf",
            )

    test.write_summary("a02b-manual-mpls-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
