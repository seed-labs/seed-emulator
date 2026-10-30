#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    # A06 demonstrates merging two emulations that share IX100.
    test.require_service(100, "ix100")
    host150 = test.require_service(150, "host0")
    test.require_service(150, "router0")
    host151 = test.require_service(151, "host0")
    test.require_service(151, "router0")

    if host150 and host151:
        test.exec_check(
            "AS150 host reaches merged AS151 host",
            host150,
            "ping -c 3 {}".format(host151.address),
        )
        test.exec_check(
            "AS151 host reaches merged AS150 host",
            host151,
            "ping -c 3 {}".format(host150.address),
        )

    test.write_summary("a06-merge-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
