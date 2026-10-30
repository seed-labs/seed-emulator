#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    host150 = test.require_service(150, "host_0")
    host152 = test.require_service(152, "host_0")
    host160 = test.require_service(160, "host_0")
    host171 = test.require_service(171, "host_0")
    host154_new = test.require_service(154, "host_new")

    if host150 and host152:
        test.exec_check("AS150 reaches AS152 across the mini Internet", host150, "ping -c 3 {} >/dev/null".format(host152.address))
    if host150 and host160:
        test.exec_check("AS150 reaches AS160 through AS3", host150, "ping -c 3 {} >/dev/null".format(host160.address))
    if host171 and host154_new:
        test.exec_check("AS171 reaches AS154 customized host", host171, "ping -c 3 {} >/dev/null".format(host154_new.address))
    if host154_new:
        test.exec_check(
            "AS154 customized host has the expected address",
            host154_new,
            "ip addr show net0 | grep -q '10.154.0.129'",
        )

    test.write_summary("b00-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
