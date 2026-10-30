#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    r0 = test.require_service(2, "r0")
    r1 = test.require_service(2, "r1")
    core0 = test.require_service(2, "core0")
    core1 = test.require_service(2, "core1")
    host150 = test.require_service(150, "host_0")
    host152 = test.require_service(152, "host_0")

    for name, router in [("r0", r0), ("r1", r1), ("core0", core0), ("core1", core1)]:
        if router:
            test.exec_check("AS2 {} starts BIRD".format(name), router, "pgrep -x bird >/dev/null")

    if r0:
        test.exec_check(
            "AS2 r0 peers with AS150 on IX100",
            r0,
            "grep -q 'neighbor 10.100.0.150 as 150' /etc/bird/bird.conf",
        )

    if r1:
        test.exec_check(
            "AS2 r1 peers with AS151 on IX101",
            r1,
            "grep -q 'neighbor 10.101.0.151 as 151' /etc/bird/bird.conf",
        )

    if host150 and host152:
        test.exec_check(
            "AS150 reaches AS152 through generated AS2 topology",
            host150,
            "ping -c 3 {} >/dev/null".format(host152.address),
        )

    test.write_summary("a15-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
