#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    # A05 demonstrates modifying a loaded component: adding web-2 to AS151,
    # adding AS154, and adding an IX102 peering point.
    web151 = test.require_service(151, "web-2")
    web154 = test.require_service(154, "web")
    test.require_service(154, "router0")
    test.require_service(154, "router1")
    test.require_service(154, "router2")
    test.require_service(102, "ix102")

    if web151 and web154:
        test.exec_check("AS151 added web service is ready", web151, "curl -fsS http://127.0.0.1 >/dev/null")
        test.exec_check("AS154 added web service is ready", web154, "curl -fsS http://127.0.0.1 >/dev/null")
        test.exec_check(
            "AS154 reaches added AS151 web service",
            web154,
            "curl -fsS http://{} >/dev/null".format(web151.address),
        )
        test.exec_check(
            "AS151 added web service reaches AS154",
            web151,
            "curl -fsS http://{} >/dev/null".format(web154.address),
        )

    test.write_summary("a05-components-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
