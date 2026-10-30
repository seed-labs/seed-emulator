#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    database = test.require_service(152, "database")
    host150 = test.require_service(150, "host_0")
    host152 = test.require_service(152, "host_0")
    host160 = test.require_service(160, "host_0")

    if database:
        test.structural_check(
            "AS152 database host has the expected fixed address",
            database.address == "10.152.0.4",
            "observed {}".format(database.address),
        )

    for service in (database, host150, host152, host160):
        if service:
            test.exec_check(
                "{} has database.com in /etc/hosts".format(service.name),
                service,
                "grep -Eq '^10\\.152\\.0\\.4[[:space:]].*database\\.com([[:space:]]|$)' /etc/hosts",
            )
            test.exec_check(
                "{} resolves database.com through /etc/hosts".format(service.name),
                service,
                "getent hosts database.com | grep -q '10.152.0.4'",
            )

    if host150:
        test.exec_check(
            "AS150 can reach the database host by custom hostname",
            host150,
            "ping -c 3 database.com >/dev/null",
        )

    test.write_summary("b21-etc-hosts-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
