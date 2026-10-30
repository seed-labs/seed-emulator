#!/usr/bin/env python3
#
# Purpose: validate the running B24 IP anycast example after TestRunner starts
# Docker Compose. Inputs come from TestRunner environment variables and compose
# labels. Outputs are JSON runtime summaries.

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


ANYCAST_ADDRESS = "10.180.0.100"


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    west_site = test.require_service(180, "host-0")
    east_site = test.require_service(180, "host-1")
    west_router = test.require_service(180, "router0")
    east_router = test.require_service(180, "router1")
    west_client = test.require_service(150, "host_0")
    east_client = test.require_service(170, "host_0")

    if west_site and east_site:
        test.structural_check(
            "AS180 anycast sites share one service address",
            west_site.address == ANYCAST_ADDRESS and east_site.address == ANYCAST_ADDRESS,
            "host-0 address={}, host-1 address={}".format(west_site.address, east_site.address),
        )
        test.exec_check(
            "IX100-side anycast web server has west marker",
            west_site,
            "curl -fsS http://127.0.0.1 | grep -q 'ix100-west'",
        )
        test.exec_check(
            "IX105-side anycast web server has east marker",
            east_site,
            "curl -fsS http://127.0.0.1 | grep -q 'ix105-east'",
        )

    if west_router:
        test.exec_check(
            "AS180 router0 advertises the anycast prefix",
            west_router,
            "birdc show route 10.180.0.0/24 | grep -q '10.180.0.0/24'",
            retries=30,
            interval=3,
            timeout=45,
        )

    if east_router:
        test.exec_check(
            "AS180 router1 advertises the anycast prefix",
            east_router,
            "birdc show route 10.180.0.0/24 | grep -q '10.180.0.0/24'",
            retries=30,
            interval=3,
            timeout=45,
        )

    if west_client:
        test.exec_check(
            "AS150 reaches the IX100-side anycast site",
            west_client,
            "curl -fsS http://{} | grep -q 'ix100-west'".format(ANYCAST_ADDRESS),
            retries=40,
            interval=5,
            timeout=45,
        )

    if east_client:
        test.exec_check(
            "AS170 reaches the IX105-side anycast site",
            east_client,
            "curl -fsS http://{} | grep -q 'ix105-east'".format(ANYCAST_ADDRESS),
            retries=40,
            interval=5,
            timeout=45,
        )

    test.write_summary("b24-ip-anycast-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
