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
    resolver = test.require_service(153, "local-dns-2", "recursive DNS resolver is generated")
    loom = test.require_service(150, "loom-registrar", "Loom Registrar frontend is generated")
    registrar = loom
    registry = test.require_service(154, "namingo-registry", "Namingo Registry is generated")
    owner_primary = test.require_service(
        160, "owner-dns-primary", "source-owned DNS Primary is generated"
    )
    owner_secondary = test.require_service(
        160, "owner-dns-secondary", "source-owned DNS Secondary is generated"
    )

    if loom:
        test.exec_check(
            "Loom serves its customer-facing web application",
            loom,
            "curl -fsS --cacert /opt/seedemu/loom/web.crt https://10.150.0.74/ | grep -q 'Loom'",
            retries=5,
            interval=3,
        )
        test.exec_check(
            "Loom initializes its provider and verifies its own EPP path",
            loom,
            "test \"$(mariadb -h 127.0.0.1 -uloom -pseedemu-loom -N loom "
            "-e \"SELECT CONCAT(type,':',api_endpoint,':',status) FROM providers "
            "WHERE tld='.com'\")\" = 'domain:epp.registry.com:700:active' "
            "&& grep -q '\"status\":\"ok\"' /run/seedemu-loom-epp-health.json "
            "&& grep -q '\"client\":\"loom\"' /run/seedemu-loom-epp-health.json "
            "&& grep -q '\"transport\":\"epp-over-tls\"' "
            "/run/seedemu-loom-epp-health.json",
            retries=10,
            interval=3,
        )
        test.exec_check(
            "Loom keeps its configuration and EPP private key out of process environment",
            loom,
            "! env | grep -q 'seedemu-epp' "
            "&& test -s /opt/loom/.env && test \"$(stat -c %a /opt/loom/.env)\" = 640 "
            "&& test \"$(stat -c %G /opt/loom/.env)\" = www-data",
            retries=1,
        )

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
            "&& getent hosts whois.registrar.com | grep -q '10.150.0.74'",
        )

    if client and owner_primary and owner_secondary:
        ssh_prefix = (
            "cred=/opt/seedemu/dns/b02a.source-owned-dns; "
            "ssh -i $cred/control.key -o BatchMode=yes -o IdentitiesOnly=yes "
            "-o UserKnownHostsFile=$cred/known_hosts "
            "-o StrictHostKeyChecking=yes -o ConnectTimeout=10"
        )
        provision = (
            "$(printf '%s' '{\"operation\":\"provision\","
            "\"zone\":\"example.com\"}' | base64 -w0)"
        )
        test.exec_check(
            "authorized source reaches its owner DNS SSH endpoints",
            client,
            "timeout 5 bash -c '</dev/tcp/11.160.0.53/22' "
            "&& timeout 5 bash -c '</dev/tcp/11.160.0.54/22'",
            retries=5,
            interval=3,
        )
        test.exec_check(
            "authorized source provisions its owner DNS secondary",
            client,
            f"{ssh_prefix} root@11.160.0.54 \"{provision}\" "
            "| grep -q '\"status\":\"provisioned\"'",
            retries=3,
            interval=3,
        )
        test.exec_check(
            "authorized source provisions its owner DNS primary",
            client,
            f"{ssh_prefix} root@11.160.0.53 \"{provision}\" "
            "| grep -q '\"status\":\"provisioned\"'",
            retries=3,
            interval=3,
        )
        test.exec_check(
            "authorized source updates and verifies its owner DNS pair",
            client,
            "cred=/opt/seedemu/dns/b02a.source-owned-dns; "
            "apply=$(printf '%s' '{\"operation\":\"apply\",\"zone\":"
            "\"example.com\",\"changes\":[{\"name\":\"www.example.com\","
            "\"record_type\":\"A\",\"operation\":\"replace\",\"ttl\":"
            "300,\"value\":\"11.160.0.80\"}]}' | base64 -w0); "
            "ssh -i $cred/control.key -o BatchMode=yes -o IdentitiesOnly=yes "
            "-o UserKnownHostsFile=$cred/known_hosts "
            "-o StrictHostKeyChecking=yes -o ConnectTimeout=10 "
            "root@11.160.0.53 \"$apply\" "
            "&& for i in 1 2 3 4 5 6 7 8 9 10; do "
            "test \"$(dig +short @11.160.0.54 www.example.com A)\" = 11.160.0.80 "
            "&& test \"$(dig +short @11.160.0.53 example.com SOA)\" "
            "= \"$(dig +short @11.160.0.54 example.com SOA)\" && break; "
            "sleep 1; done "
            "&& test \"$(dig +short @11.160.0.53 www.example.com A)\" = 11.160.0.80 "
            "&& test \"$(dig +short @11.160.0.54 www.example.com A)\" = 11.160.0.80 "
            "&& test \"$(dig +short @11.160.0.53 example.com SOA)\" "
            "= \"$(dig +short @11.160.0.54 example.com SOA)\"",
            retries=3,
            interval=3,
        )

    if registrar:
        test.exec_check(
            "Namingo Registrar uses its upstream Loom backend adapter",
            registrar,
            "grep -q '\"backend\" => \"loom\"' /opt/registrar/whois/config.php "
            "&& grep -q '\"db_host\" => \"127.0.0.1\"' /opt/registrar/whois/config.php "
            "&& grep -q '\"backend\" => \"loom\"' /opt/registrar/rdap/config.php "
            "&& mariadb -h 127.0.0.1 -P 3306 -uloom_rdds -pseedemu-loom-rdds "
            "-N loom -e 'SELECT COUNT(*) FROM providers' | grep -qx 1",
            retries=10,
            interval=3,
        )
        test.exec_check(
            "Namingo Registrar provides only Loom-backed WHOIS/RDAP",
            registrar,
            "pgrep -f start_whois.php >/dev/null "
            "&& pgrep -f start_rdap.php >/dev/null "
            "&& grep -q 'whois.registrar.com' /opt/registrar/whois/config.php "
            "&& grep -q 'listen 8080' /etc/nginx/sites-available/namingo-rdap "
            "&& grep -q 'listen 443 ssl' /etc/nginx/sites-available/default "
            "&& test ! -e /usr/local/bin/seedemu-epp-client "
            "&& test ! -e /opt/seedemu/namingo/epp-client.php "
            "&& test ! -e /run/seedemu-epp-health.json",
            retries=3,
            interval=3,
        )
    if registry:
        test.exec_check(
            "Namingo Registry starts EPP and Registry-backed RDDS for COM",
            registry,
            "pgrep -f start_epp.php >/dev/null "
            "&& pgrep -f start_whois.php >/dev/null "
            "&& pgrep -f start_rdap.php >/dev/null "
            "&& grep -q 'rdap.registry.com' /opt/registry/rdap/config.php "
            "&& grep -q '\"epp_port\" => 700' /opt/registry/epp/config.php "
            "&& grep -q 'epp.registry.com' /usr/local/bin/seedemu-start-namingo-registry "
            "&& grep -q '10.150.0.74' /opt/seedemu/namingo/bootstrap.php "
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
