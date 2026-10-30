#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    web150 = test.require_service(150, "web")
    web151 = test.require_service(151, "web")
    web152 = test.require_service(152, "web")

    if web150 and web151 and web152:
        test.exec_check("AS151 fetches AS150 web service", web151, "curl -fsS http://{} >/dev/null".format(web150.address))
        test.exec_check("AS152 fetches AS151 web service", web152, "curl -fsS http://{} >/dev/null".format(web151.address))
        test.exec_check("AS150 reaches AS152 by ICMP", web150, "ping -c 3 {} >/dev/null".format(web152.address))

    test.write_summary("a00-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
