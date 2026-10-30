#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


AS151_RANGE = r"10\.151\.0\.(12[5-9]|13[0-9]|140)"
AS161_RANGE = r"10\.161\.0\.(10[1-9]|11[0-9]|120)"


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    server151 = test.require_service(151, "dhcp-server-01")
    server161 = test.require_service(161, "dhcp-server-02")
    client151_1 = test.require_service(151, "dhcp-client-01")
    client151_2 = test.require_service(151, "dhcp-client-02")
    client161_1 = test.require_service(161, "dhcp-client-03")
    client161_2 = test.require_service(161, "dhcp-client-04")

    if server151:
        test.exec_check("AS151 DHCP server is running", server151, "pgrep dhcpd >/dev/null")
        test.exec_check(
            "AS151 DHCP server advertises custom range",
            server151,
            "grep -q 'range 10.151.0.125 10.151.0.140;' /etc/dhcp/dhcpd.conf",
        )
        test.exec_check(
            "AS151 DHCP server advertises the subnet router",
            server151,
            "grep -q 'option routers 10.151.0.254;' /etc/dhcp/dhcpd.conf",
        )

    if server161:
        test.exec_check("AS161 DHCP server is running", server161, "pgrep dhcpd >/dev/null")
        test.exec_check(
            "AS161 DHCP server advertises default range",
            server161,
            "grep -q 'range 10.161.0.101 10.161.0.120;' /etc/dhcp/dhcpd.conf",
        )
        test.exec_check(
            "AS161 DHCP server advertises the subnet router",
            server161,
            "grep -q 'option routers 10.161.0.254;' /etc/dhcp/dhcpd.conf",
        )

    for client in (client151_1, client151_2):
        if client:
            test.exec_check(
                "{} has the DHCP client helper".format(client.name),
                client,
                "test -x dhclient.sh",
            )
            test.exec_check(
                "{} received an AS151 DHCP lease".format(client.name),
                client,
                "ip -4 addr show net0 | grep -Eq '{}/'".format(AS151_RANGE),
            )
            test.exec_check(
                "{} installed the AS151 DHCP default route".format(client.name),
                client,
                "ip route | grep -q '^default via 10.151.0.254'",
            )

    for client in (client161_1, client161_2):
        if client:
            test.exec_check(
                "{} has the DHCP client helper".format(client.name),
                client,
                "test -x dhclient.sh",
            )
            test.exec_check(
                "{} received an AS161 DHCP lease".format(client.name),
                client,
                "ip -4 addr show net0 | grep -Eq '{}/'".format(AS161_RANGE),
            )
            test.exec_check(
                "{} installed the AS161 DHCP default route".format(client.name),
                client,
                "ip route | grep -q '^default via 10.161.0.254'",
            )

    test.write_summary("b20-dhcp-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
