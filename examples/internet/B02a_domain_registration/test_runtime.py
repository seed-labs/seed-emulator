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
            "COM-A exposes only the restricted Registry zone receiver",
            a_com,
            "pgrep -x sshd >/dev/null "
            "&& grep -q 'from=\"10.154.0.73\",restrict,command=' /root/.ssh/authorized_keys "
            "&& grep -q 'seedemu-install-zone-com' /root/.ssh/authorized_keys "
            "&& grep -q 'test \"$new_serial\" -gt \"$old_serial\"' "
            "/usr/local/sbin/seedemu-install-zone-com",
        )
        test.exec_check(
            "Registry Zone Writer securely replaces the COM source zone",
            a_com,
            "test \"$(named-checkzone -D -o - com. /etc/bind/zones/com. 2>/dev/null "
            "| awk '$4 == \"SOA\" {print $7; exit}')\" -gt 1",
            retries=5,
            interval=3,
        )
        test.exec_check(
            "COM-A rejects ordinary COM queries",
            a_com,
            "! dig @127.0.0.1 com. SOA +norecurse +time=1 +tries=1 | grep -q 'status: NOERROR'",
        )
        test.exec_check(
            "COM-A rejects a valid zone with a rolled-back SOA serial",
            a_com,
            "before=$(named-checkzone -D -o - com. /etc/bind/zones/com. 2>/dev/null "
            "| awk '$4 == \"SOA\" {print $7; exit}'); "
            "candidate=$(mktemp); trap 'rm -f \"$candidate\"' EXIT; "
            "lower=$((before - 1)); "
            "sed \"0,/$before/s//$lower/\" /etc/bind/zones/com. > \"$candidate\"; "
            "named-checkzone com. \"$candidate\" >/dev/null; "
            "if /usr/local/sbin/seedemu-install-zone-com < \"$candidate\"; then exit 1; fi; "
            "after=$(named-checkzone -D -o - com. /etc/bind/zones/com. 2>/dev/null "
            "| awk '$4 == \"SOA\" {print $7; exit}'); test \"$after\" = \"$before\"",
            retries=1,
        )

    for name, server in (("COM-B", b_com), ("COM-C", c_com)):
        if server:
            test.exec_check(
                "{} only transfers COM from COM-A with TSIG".format(name),
                server,
                "grep -q 'type slave' /etc/bind/named.conf.zones "
                "&& grep -q '10.151.0.71 key \"com-transfer\"' /etc/bind/named.conf.zones",
            )
            test.exec_check(
                "{} serves the transferred COM zone".format(name),
                server,
                "test \"$(dig @127.0.0.1 com. SOA +norecurse +short | awk '{print $3}')\" -gt 1",
                retries=5,
                interval=3,
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
            "Namingo Registrar starts WHOIS/RDAP and completes verified EPP over TLS",
            registrar,
            "pgrep -f start_whois.php >/dev/null "
            "&& pgrep -f start_rdap.php >/dev/null "
            "&& grep -q 'whois.registrar.com' /opt/registrar/whois/config.php "
            "&& grep -q '\"status\":\"ok\"' /run/seedemu-epp-health.json "
            "&& grep -q '\"transport\":\"epp-over-tls\"' /run/seedemu-epp-health.json "
            "&& grep -q \"'verify_peer' => true\" /usr/local/bin/seedemu-epp-client "
            "&& grep -q \"'verify_peer_name' => true\" /usr/local/bin/seedemu-epp-client "
            "&& /usr/local/bin/seedemu-epp-client check runtime-check.com "
            "| grep -q '\"status\":\"ok\"'",
            retries=3,
            interval=3,
        )
        test.exec_check(
            "Namingo EPP client creates contacts, domains, hosts, and updates delegation",
            registrar,
            "/usr/local/bin/seedemu-epp-client contact-create "
            "'{\"id\":\"SEED-RUNTIME\",\"firstname\":\"Seed\",\"lastname\":\"Emu\","
            "\"address1\":\"1 Simulation Way\",\"city\":\"Test City\","
            "\"postcode\":\"10000\",\"country\":\"US\","
            "\"fullphonenumber\":\"+1.5550100\",\"email\":\"runtime@registrar.com\","
            "\"authInfoPw\":\"Contact-Runtime-1\"}' "
            "&& /usr/local/bin/seedemu-epp-client domain-create "
            "'{\"domainname\":\"runtime-registration.com\",\"period\":1,"
            "\"registrant\":\"SEED-RUNTIME\",\"contacts\":{\"admin\":\"SEED-RUNTIME\","
            "\"tech\":\"SEED-RUNTIME\",\"billing\":\"SEED-RUNTIME\"},"
            "\"authInfoPw\":\"Domain-Runtime-1\"}' "
            "&& /usr/local/bin/seedemu-epp-client host-create "
            "'{\"hostname\":\"ns1.runtime-registration.com\",\"ipaddress\":\"11.150.0.71\"}' "
            "&& /usr/local/bin/seedemu-epp-client host-create "
            "'{\"hostname\":\"ns2.runtime-registration.com\",\"ipaddress\":\"11.150.0.73\"}' "
            "&& /usr/local/bin/seedemu-epp-client domain-update "
            "'{\"domainname\":\"runtime-registration.com\",\"nameservers\":["
            "\"ns1.runtime-registration.com\",\"ns2.runtime-registration.com\"]}' "
            "| grep -q '\"status\":\"ok\"'",
            retries=1,
            interval=3,
        )
        test.exec_check(
            "Namingo Registry rejects an incorrect EPP password",
            registrar,
            "work=$(mktemp -d); trap 'rm -f \"$work/config.php\" \"$work/client\" \"$work/out\"; rmdir \"$work\"' EXIT; "
            "sed 's/\"password\" => \"[^\"]*\"/\"password\" => \"wrong-password\"/' "
            "/opt/seedemu/namingo/epp-client.php > \"$work/config.php\"; "
            "sed \"s#/opt/seedemu/namingo/epp-client.php#$work/config.php#\" "
            "/usr/local/bin/seedemu-epp-client > \"$work/client\"; chmod 700 \"$work/client\"; "
            "if \"$work/client\" check rejected-password.com >\"$work/out\" 2>&1; then exit 1; fi; "
            "grep -q 'EPP login failed' \"$work/out\"",
            retries=1,
        )
        test.exec_check(
            "Namingo Registry rejects an untrusted EPP client certificate",
            registrar,
            "work=$(mktemp -d); trap 'rm -f \"$work/config.php\" \"$work/client\" \"$work/client.key\" \"$work/client.crt\"; rmdir \"$work\"' EXIT; "
            "openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes "
            "-days 1 -subj /CN=untrusted-registrar -keyout \"$work/client.key\" "
            "-out \"$work/client.crt\" >/dev/null 2>&1; "
            "sed -e \"s#/opt/seedemu/namingo/epp-client.crt#$work/client.crt#\" "
            "-e \"s#/opt/seedemu/namingo/epp-client.key#$work/client.key#\" "
            "/opt/seedemu/namingo/epp-client.php > \"$work/config.php\"; "
            "sed \"s#/opt/seedemu/namingo/epp-client.php#$work/config.php#\" "
            "/usr/local/bin/seedemu-epp-client > \"$work/client\"; chmod 700 \"$work/client\"; "
            "if \"$work/client\" check rejected-certificate.com >/dev/null 2>&1; then exit 1; fi",
            retries=1,
        )

    if b_com:
        test.exec_check(
            "Registry registration reaches the public COM delegation",
            b_com,
            "dig @127.0.0.1 runtime-registration.com NS +norecurse +noall +authority "
            "| awk '$4 == \"NS\" {print $5}' | grep -q 'ns1.runtime-registration.com.' "
            "&& dig @127.0.0.1 runtime-registration.com NS +norecurse +noall +additional "
            "| awk '$1 == \"ns1.runtime-registration.com.\" && $4 == \"A\" {print $5}' "
            "| grep -q '11.150.0.71'",
            retries=15,
            interval=3,
        )

    if registry:
        test.exec_check(
            "Namingo Registry starts EPP for COM",
            registry,
            "pgrep -f start_epp.php >/dev/null "
            "&& grep -q '\"epp_port\" => 700' /opt/registry/epp/config.php "
            "&& grep -q 'epp.registry.com' /usr/local/bin/seedemu-start-namingo-registry "
            "&& grep -q '10.150.0.73' /opt/seedemu/namingo/bootstrap.php "
            "&& openssl x509 -in /opt/seedemu/namingo/tls/epp.crt -noout "
            "-checkhost epp.registry.com | grep -q 'does match certificate' "
            "&& test -s /opt/seedemu/namingo/zone-publisher-key "
            "&& grep -q 'StrictHostKeyChecking=yes' /usr/local/bin/seedemu-publish-namingo-zone "
            "&& grep -q '10.151.0.71 ssh-ed25519' /opt/seedemu/namingo/known_hosts",
        )
        test.exec_check(
            "Registry contains only the configured COM TLD",
            registry,
            "test \"$(mariadb -N registry -e 'SELECT GROUP_CONCAT(tld ORDER BY tld) FROM domain_tld')\" "
            "= '.com' && test ! -e /var/lib/bind/test.zone "
            "&& test ! -e /var/lib/bind/com.test.zone",
            retries=1,
        )
        test.exec_check(
            "COM-A rejects an unauthorized SSH publisher key",
            registry,
            "work=$(mktemp -d); trap 'rm -f \"$work/key\" \"$work/key.pub\"; rmdir \"$work\"' EXIT; "
            "ssh-keygen -q -t ed25519 -N '' -f \"$work/key\"; "
            "if ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes "
            "-o UserKnownHostsFile=/opt/seedemu/namingo/known_hosts -i \"$work/key\" "
            "root@10.151.0.71 true >/dev/null 2>&1; then exit 1; fi",
            retries=1,
        )

    test.write_summary("b02a-tld-dns-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
