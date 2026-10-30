#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    host151 = test.require_service(151, "host0")
    host152 = test.require_service(152, "host0")
    host153 = test.require_service(153, "host0")
    test.require_service(2, "r1")
    test.require_service(2, "r2")
    test.require_service(2, "r3")
    test.require_service(2, "r4")

    if host151 and host152:
        test.exec_check("AS151 reaches AS152 through transit AS2", host151, "ping -c 3 {} >/dev/null".format(host152.address))
    if host151 and host153:
        test.exec_check("AS151 reaches AS153 through transit AS2", host151, "ping -c 3 {} >/dev/null".format(host153.address))
    if host152 and host151:
        test.exec_check("AS152 reaches AS151 through transit AS2", host152, "ping -c 3 {} >/dev/null".format(host151.address))

    test.write_summary("a01-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
