#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    a_com = test.require_service(151, "host_0", "COM-A hidden primary is generated")
    b_com = test.require_service(152, "host_0", "COM-B public secondary is generated")
    c_com = test.require_service(153, "c-com", "COM-C public secondary is generated")
    root = test.require_service(171, "host_0", "root primary is generated")
    client = test.require_service(150, "host_1", "representative DNS client is generated")
    registrar = test.require_service(150, "namingo-registrar", "Namingo Registrar is generated")
    registry = test.require_service(154, "namingo-registry", "Namingo Registry is generated")

    if a_com:
        test.exec_check(
            "COM-A is a query-hidden TSIG-protected primary",
            a_com,
            "grep -q 'allow-query { none; }' /etc/bind/named.conf.zones "
            "&& grep -q 'allow-update { none; }' /etc/bind/named.conf.zones "
            "&& grep -q 'allow-transfer { key \"com-transfer\"; }' /etc/bind/named.conf.zones "
            "&& grep -q '10.152.0.71 key \"com-transfer\"' /etc/bind/named.conf.zones "
            "&& grep -q '10.153.0.73 key \"com-transfer\"' /etc/bind/named.conf.zones",
        )
        test.exec_check(
            "COM-A rejects ordinary COM queries",
            a_com,
            "! dig @127.0.0.1 com. SOA +norecurse +time=1 +tries=1 | grep -q 'status: NOERROR'",
        )

    for name, server in (("COM-B", b_com), ("COM-C", c_com)):
        if server:
            test.exec_check(
                "{} only transfers COM from COM-A with TSIG".format(name),
                server,
                "grep -q 'type slave' /etc/bind/named.conf.zones "
                "&& grep -q '10.151.0.71 key \"com-transfer\"' /etc/bind/named.conf.zones "
                "&& grep -q 'allow-update { none; }' /etc/bind/named.conf.zones",
            )
            test.exec_check(
                "{} serves the transferred COM zone".format(name),
                server,
                "dig @127.0.0.1 com. SOA +norecurse +short | grep -q .",
                retries=30,
                interval=2,
            )

    if root:
        test.exec_check(
            "root publishes COM-B and COM-C but not COM-A",
            root,
            "grep -q '10.152.0.71' /etc/bind/zones/root "
            "&& grep -q '10.153.0.73' /etc/bind/zones/root "
            "&& ! grep -q '10.151.0.71' /etc/bind/zones/root",
        )

    if client:
        test.exec_check(
            "ordinary recursive DNS still resolves inherited zones",
            client,
            "getent hosts example.net | grep -q '3.3.3.3'",
        )
        test.exec_check(
            "Namingo service names resolve through public COM secondaries",
            client,
            "getent hosts epp.registry.com | grep -q '10.154.0.73' "
            "&& getent hosts whois.registrar.com | grep -q '10.150.0.73'",
        )

    if registrar:
        test.exec_check(
            "Namingo Registrar starts WHOIS and RDAP",
            registrar,
            "pgrep -f start_whois.php >/dev/null "
            "&& pgrep -f start_rdap.php >/dev/null "
            "&& grep -q 'whois.registrar.com' /opt/registrar/whois/config.php",
        )

    if registry:
        test.exec_check(
            "Namingo Registry starts EPP for COM",
            registry,
            "pgrep -f start_epp.php >/dev/null "
            "&& grep -q '\"epp_port\" => 700' /opt/registry/epp/config.php "
            "&& grep -q 'epp.registry.com' /usr/local/bin/seedemu-start-namingo-registry "
            "&& grep -q '10.150.0.73' /opt/seedemu/namingo/bootstrap.php",
        )

    test.write_summary("b02a-tld-dns-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
