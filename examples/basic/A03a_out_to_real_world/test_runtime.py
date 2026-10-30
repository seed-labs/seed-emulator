#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    web151 = test.require_service(151, "web")
    web152 = test.require_service(152, "web")
    akamai = test.require_service(20940, "rw", "Akamai real-world router is generated")
    router151 = test.require_service(151, "router0")

    if web151 and web152:
        test.exec_check("AS151 fetches AS152 web service", web151, "curl -fsS http://{} >/dev/null".format(web152.address))

    if akamai:
        test.exec_check(
            "Akamai real-world router has deterministic example prefix",
            akamai,
            "grep -q '23.192.228.0/24' /etc/bird/bird.conf",
        )
        test.exec_check(
            "Akamai real-world router has service-network route setup",
            akamai,
            "test -s /rw_configure_script && grep -q 'MASQUERADE' /rw_configure_script && grep -q 'sed -i' /rw_configure_script",
        )

    if router151:
        test.exec_check("OpenVPN remote access is absent from out-to-real-world example", router151, "test ! -e /ovpn-server.conf")

    test.write_summary("a03a-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
