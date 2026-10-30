#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    web151 = test.require_service(151, "web")
    web152 = test.require_service(152, "web")
    r1 = test.require_service(2, "r1")
    r2 = test.require_service(2, "r2")
    r3 = test.require_service(2, "r3")
    r4 = test.require_service(2, "r4")

    if web151 and web152:
        test.exec_check("AS151 fetches AS152 web service", web151, "curl -fsS http://{} >/dev/null".format(web152.address))
        test.exec_check("AS152 fetches AS151 web service", web152, "curl -fsS http://{} >/dev/null".format(web151.address))

    if r1:
        test.exec_check(
            "r1 has MPLS/LDP enabled on the internal transit network",
            r1,
            "test -s /mpls_ifaces.txt && grep -q '^net0$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r2:
        test.exec_check(
            "r2 is an MPLS non-edge router with both internal links enabled",
            r2,
            "grep -q '^net0$' /mpls_ifaces.txt && grep -q '^net1$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r3:
        test.exec_check(
            "r3 is an MPLS non-edge router with both internal links enabled",
            r3,
            "grep -q '^net1$' /mpls_ifaces.txt && grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r4:
        test.exec_check(
            "r4 has MPLS/LDP enabled on the internal transit network",
            r4,
            "test -s /mpls_ifaces.txt && grep -q '^net2$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )

    test.write_summary("a02-mpls-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
