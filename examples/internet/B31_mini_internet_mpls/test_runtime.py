#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    host150 = test.require_service(150, "host_0")
    host152 = test.require_service(152, "host_0")
    host171 = test.require_service(171, "host_0")
    host154_new = test.require_service(154, "host_new")
    r100 = test.require_service(2, "r100")
    r101 = test.require_service(2, "r101")
    r102 = test.require_service(2, "r102")
    r105 = test.require_service(2, "r105")
    core_100_101 = test.require_service(2, "core_100_101")
    as3_r103 = test.require_service(3, "r103")

    if host150 and host152:
        test.exec_check("AS150 reaches AS152 through AS2", host150, "ping -c 3 {} >/dev/null".format(host152.address))
    if host171 and host154_new:
        test.exec_check("AS171 reaches AS154 customized host", host171, "ping -c 3 {} >/dev/null".format(host154_new.address))

    if r100:
        test.exec_check(
            "AS2 r100 has MPLS/LDP enabled on internal links",
            r100,
            "grep -q '^net_100_core_100_101$' /mpls_ifaces.txt && grep -q '^net_100_core_100_105$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r101:
        test.exec_check(
            "AS2 r101 has MPLS/LDP enabled on internal links",
            r101,
            "grep -q '^net_core_100_101_101$' /mpls_ifaces.txt && grep -q '^net_101_core_101_102$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r102:
        test.exec_check(
            "AS2 r102 has MPLS/LDP enabled on internal links",
            r102,
            "grep -q '^net_core_101_102_102$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if r105:
        test.exec_check(
            "AS2 r105 has MPLS/LDP enabled on internal links",
            r105,
            "grep -q '^net_core_100_105_105$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if core_100_101:
        test.exec_check(
            "AS2 core router participates in MPLS/LDP only on internal links",
            core_100_101,
            "grep -q '^net_100_core_100_101$' /mpls_ifaces.txt && grep -q '^net_core_100_101_101$' /mpls_ifaces.txt && grep -q 'mpls ldp' /etc/frr/frr.conf",
        )
    if as3_r103:
        test.exec_check("AS3 remains a non-MPLS transit AS", as3_r103, "test ! -e /mpls_ifaces.txt")

    test.write_summary("b31-mpls-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
