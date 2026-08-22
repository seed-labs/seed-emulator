#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from seedemu.testing import ComposeRuntimeTest


POLICY_PATH = "/opt/seedemu-agent-registrar/policy.json"


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    def check(name, service, command, retries=1, interval=0, timeout=10):
        """Run a fast check and report it immediately."""

        result = test.exec_check(
            name,
            service,
            command,
            retries=retries,
            interval=interval,
            timeout=timeout,
        )
        print(
            "{} {} ({} attempt{})".format(
                result["status"].upper(),
                name,
                result["attempts"],
                "" if result["attempts"] == 1 else "s",
            ),
            flush=True,
        )
        return result

    def wait_check(name, service, command, retries=40):
        """Poll one short command without nesting another shell retry loop."""

        return check(
            name,
            service,
            command,
            retries=retries,
            interval=1,
            timeout=5,
        )

    registrar = test.require_service(150, "registrar")
    com_master = test.require_service(151, "host_0")
    com_secondary = test.require_service(152, "host_0")
    managed_dns_master = test.require_service(161, "managed-dns-master")
    managed_dns_secondary = test.require_service(162, "managed-dns-secondary")
    client = test.require_service(150, "host_0")
    host160 = test.require_service(160, "host_0")
    host170 = test.require_service(170, "host_0")
    host164 = test.require_service(164, "host_0")
    ns_example_net = test.require_service(163, "host_0")

    if registrar:
        check(
            "registrar container receives the dynamic TLD policy",
            registrar,
            "test -r {} && grep -q '\"com\"' {} "
            "&& grep -q 'ns1.seedemu-dns.net' {} "
            "&& grep -q 'ns2.seedemu-dns.net' {}".format(
                POLICY_PATH, POLICY_PATH, POLICY_PATH, POLICY_PATH
            ),
        )
        check(
            "an unclaimed valid .com domain is available",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com/availability "
            "| grep -q '\"available\":true'",
        )
        check(
            "purchase atomically creates a provisioning order",
            registrar,
            "curl -fsS -X POST http://127.0.0.1:8080/v1/purchases "
            "-H 'Content-Type: application/json' -H 'Idempotency-Key: b02a-alice' "
            "--data '{\"domain\":\"alice-shop.com\","
            "\"registrant_id\":\"alice\",\"years\":1}' >/tmp/alice-purchase.json "
            "&& python3 -c 'import json; d=json.load(open(\"/tmp/alice-purchase.json\")); "
            "assert d[\"status\"] in {\"provisioning\",\"active\"}; "
            "assert d[\"domain_name\"] == \"alice-shop.com.\"; "
            "open(\"/tmp/alice-order-id\",\"w\").write(d[\"id\"])'",
        )
        check(
            "same idempotency key returns the same order",
            registrar,
            "curl -fsS -X POST http://127.0.0.1:8080/v1/purchases "
            "-H 'Content-Type: application/json' -H 'Idempotency-Key: b02a-alice' "
            "--data '{\"domain\":\"alice-shop.com\","
            "\"registrant_id\":\"alice\",\"years\":1}' >/tmp/alice-repeat.json "
            "&& python3 -c 'import json; d=json.load(open(\"/tmp/alice-repeat.json\")); "
            "assert d[\"id\"] == open(\"/tmp/alice-order-id\").read()'",
        )
        check(
            "idempotency key conflict is rejected",
            registrar,
            "test \"$(curl -sS -o /tmp/idempotency-conflict.json -w '%{http_code}' "
            "-X POST http://127.0.0.1:8080/v1/purchases "
            "-H 'Content-Type: application/json' -H 'Idempotency-Key: b02a-alice' "
            "--data '{\"domain\":\"different-shop.com\","
            "\"registrant_id\":\"alice\",\"years\":1}')\" = 409 "
            "&& grep -q 'idempotency_key_conflict' /tmp/idempotency-conflict.json",
        )
        check(
            "a claimed domain is no longer available",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com/availability "
            "| grep -q '\"available\":false'",
        )
        wait_check(
            "outbox provisions the zone, delegation, and activates the order",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/orders/$(cat /tmp/alice-order-id) "
            "| grep -q '\"status\":\"active\"' && "
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com "
            "| grep -q '\"zone_status\":\"active\"'",
        )
        check(
            "repeating zone provisioning is idempotent",
            registrar,
            "curl -fsS -X POST http://127.0.0.1:8053/v1/zones "
            "-H 'Content-Type: application/json' --data '{"
            "\"domain\":\"alice-shop.com\",\"nameservers\":["
            "{\"name\":\"ns1.seedemu-dns.net.\",\"address\":\"10.161.0.53\"},"
            "{\"name\":\"ns2.seedemu-dns.net.\",\"address\":\"10.162.0.53\"}]}' "
            "| grep -q '\"changed\":false'",
        )
        check(
            "owner can submit an A record through the managed DNS API",
            registrar,
            "curl -fsS -X PUT http://127.0.0.1:8080/v1/domains/alice-shop.com/records/www-a "
            "-H 'Content-Type: application/json' --data '{\"registrant_id\":\"alice\","
            "\"name\":\"www.alice-shop.com\",\"record_type\":\"A\","
            "\"ttl\":30,\"value\":\"10.150.0.71\"}' >/dev/null",
        )
        wait_check(
            "the submitted A record becomes active",
            registrar,
            "curl -fsS "
            "-H 'X-Registrant-ID: alice' "
            "http://127.0.0.1:8080/v1/domains/alice-shop.com/records "
            "| grep -q '\"status\":\"active\"'",
        )
        check(
            "non-owner managed DNS write is rejected",
            registrar,
            "test \"$(curl -sS -o /tmp/non-owner.json -w '%{http_code}' -X PUT "
            "http://127.0.0.1:8080/v1/domains/alice-shop.com/records/intruder "
            "-H 'Content-Type: application/json' --data '{\"registrant_id\":\"mallory\","
            "\"name\":\"bad.alice-shop.com\",\"record_type\":\"A\","
            "\"ttl\":30,\"value\":\"10.150.0.71\"}')\" = 403 "
            "&& grep -q 'not_domain_owner' /tmp/non-owner.json",
        )
        check(
            "in-bailiwick nameservers create and verify parent glue",
            registrar,
            "curl -fsS -X POST http://127.0.0.1:8053/v1/delegations "
            "-H 'Content-Type: application/json' --data '{"
            "\"domain\":\"glue-test.com\",\"nameservers\":["
            "{\"name\":\"ns1.glue-test.com.\",\"address\":\"10.161.0.53\"},"
            "{\"name\":\"ns2.glue-test.com.\",\"address\":\"10.162.0.53\"}]}' "
            "| grep -q '\"glue\":\['",
            timeout=45,
        )
        check(
            "in-bailiwick nameserver without an address is rejected",
            registrar,
            "test \"$(curl -sS -o /tmp/missing-glue.json -w '%{http_code}' "
            "-X POST http://127.0.0.1:8053/v1/delegations "
            "-H 'Content-Type: application/json' --data '{"
            "\"domain\":\"missing-glue.com\",\"nameservers\":["
            "{\"name\":\"ns1.missing-glue.com.\"},"
            "{\"name\":\"ns2.missing-glue.com.\",\"address\":\"10.162.0.53\"}]}'"
            ")\" = 400 && grep -q 'requires a glue address' /tmp/missing-glue.json",
        )
        check(
            "concurrent purchases create one owner, order, and outbox event",
            registrar,
            "rm -f /tmp/race-code-* /tmp/race-body-*; "
            "for i in 1 2 3 4 5 6; do "
            "(curl -sS -o /tmp/race-body-$i -w '%{http_code}' -X POST "
            "http://127.0.0.1:8080/v1/purchases -H 'Content-Type: application/json' "
            "-H \"Idempotency-Key: race-$i\" --data \"{\\\"domain\\\":\\\"race-shop.com\\\","
            "\\\"registrant_id\\\":\\\"buyer-$i\\\",\\\"years\\\":1}\" "
            ">/tmp/race-code-$i) & done; wait; "
            "test \"$(grep -l '^201$' /tmp/race-code-* | wc -l)\" = 1 "
            "&& test \"$(grep -l '^409$' /tmp/race-code-* | wc -l)\" = 5 "
            "&& python3 -c 'import sqlite3; c=sqlite3.connect("
            "\"/var/lib/seedemu-agent-registrar/registrar.db\"); "
            "assert c.execute(\"select count(*) from domains where name=?\","
            "(\"race-shop.com.\",)).fetchone()[0] == 1; "
            "assert c.execute(\"select count(*) from orders where domain_name=?\","
            "(\"race-shop.com.\",)).fetchone()[0] == 1; "
            "assert c.execute(\"select count(*) from outbox where event_type=? and aggregate_id=?\","
            "(\"domain.provision_requested\",\"race-shop.com.\")).fetchone()[0] == 1'",
        )
        wait_check(
            "the concurrent winner is eventually provisioned",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/domains/race-shop.com "
            "| grep -q '\"status\":\"active\"' && "
            "python3 -c 'import sqlite3; c=sqlite3.connect("
            "\"/var/lib/seedemu-agent-registrar/registrar.db\"); "
            "assert c.execute(\"select status from outbox where event_type=? and aggregate_id=?\","
            "(\"domain.provision_requested\",\"race-shop.com.\")).fetchone()[0] == \"completed\"'",
        )

    expected_delegation = (
        "test \"$(dig +noall +authority @{} alice-shop.com NS "
        "| awk '$4 == \"NS\" {{print $5}}' | sort | tr '\\n' ' ')\" = "
        "\"ns1.seedemu-dns.net. ns2.seedemu-dns.net. \""
    )
    if com_master:
        check(
            "com master contains the new delegation",
            com_master,
            expected_delegation.format("127.0.0.1"),
        )
        check(
            "com master contains generated in-bailiwick glue",
            com_master,
            "dig +norecurse +noall +additional @127.0.0.1 glue-test.com NS "
            "| grep -Eq '^ns1[.]glue-test[.]com[.][[:space:]]+[0-9]+"
            "[[:space:]]+IN[[:space:]]+A[[:space:]]+10[.]161[.]0[.]53$' "
            "&& dig +norecurse +noall +additional @127.0.0.1 glue-test.com NS "
            "| grep -Eq '^ns2[.]glue-test[.]com[.][[:space:]]+[0-9]+"
            "[[:space:]]+IN[[:space:]]+A[[:space:]]+10[.]162[.]0[.]53$'",
        )
    if com_secondary:
        check(
            "com secondary received the delegation through zone transfer",
            com_secondary,
            expected_delegation.format("127.0.0.1"),
        )
        check(
            "com secondary received generated in-bailiwick glue",
            com_secondary,
            "dig +norecurse +noall +additional @127.0.0.1 glue-test.com NS "
            "| grep -Eq '^ns1[.]glue-test[.]com[.][[:space:]]+[0-9]+"
            "[[:space:]]+IN[[:space:]]+A[[:space:]]+10[.]161[.]0[.]53$' "
            "&& dig +norecurse +noall +additional @127.0.0.1 glue-test.com NS "
            "| grep -Eq '^ns2[.]glue-test[.]com[.][[:space:]]+[0-9]+"
            "[[:space:]]+IN[[:space:]]+A[[:space:]]+10[.]162[.]0[.]53$'",
        )

    if managed_dns_master:
        test.structural_check(
            "managed DNS master has the expected fixed address",
            managed_dns_master.address == "10.161.0.53",
            "observed {}".format(managed_dns_master.address),
        )
        check(
            "managed DNS master is running named",
            managed_dns_master,
            "pgrep named >/dev/null",
        )
        check(
            "managed DNS master created a valid persistent zone and include",
            managed_dns_master,
            "test -s /var/lib/seedemu-managed-dns/zones/db.alice-shop.com "
            "&& test -s /var/lib/seedemu-managed-dns/includes/alice-shop.com.conf "
            "&& named-checkzone alice-shop.com "
            "/var/lib/seedemu-managed-dns/zones/db.alice-shop.com >/dev/null "
            "&& named-checkconf",
        )
        check(
            "managed DNS master holds update and transfer keys",
            managed_dns_master,
            "test -s /etc/bind/managed-update.key "
            "&& test -s /etc/bind/managed-transfer.key",
        )
        check(
            "managed DNS master answers the provisioned record",
            managed_dns_master,
            "test \"$(dig +short @127.0.0.1 www.alice-shop.com A)\" = \"10.150.0.71\"",
        )

    if managed_dns_secondary:
        test.structural_check(
            "managed DNS secondary has the expected fixed address",
            managed_dns_secondary.address == "10.162.0.53",
            "observed {}".format(managed_dns_secondary.address),
        )
        check(
            "managed DNS secondary is running named",
            managed_dns_secondary,
            "pgrep named >/dev/null",
        )
        check(
            "managed DNS secondary only receives the transfer key",
            managed_dns_secondary,
            "test ! -e /etc/bind/managed-update.key "
            "&& test -s /etc/bind/managed-transfer.key",
        )
        check(
            "managed DNS secondary exposes the expected SOA and NS records",
            managed_dns_secondary,
            "test -n \"$(dig +short @127.0.0.1 alice-shop.com SOA)\" "
            "&& test \"$(dig +short @127.0.0.1 alice-shop.com NS "
            "| sort | tr '\\n' ' ')\" = "
            "\"ns1.seedemu-dns.net. ns2.seedemu-dns.net. \"",
        )
        check(
            "managed DNS secondary received the zone and record through AXFR",
            managed_dns_secondary,
            "test \"$(dig +short @127.0.0.1 www.alice-shop.com A)\" = \"10.150.0.71\"",
        )

    if client:
        check(
            "managed DNS provider names resolve through the DNS hierarchy",
            client,
            "test \"$(dig +short ns1.seedemu-dns.net A)\" = \"10.161.0.53\" "
            "&& test \"$(dig +short ns2.seedemu-dns.net A)\" = \"10.162.0.53\"",
        )

    if client:
        check(
            "recursive DNS resolves the separately added application A record",
            client,
            "test \"$(dig +short www.alice-shop.com A)\" = \"10.150.0.71\"",
        )

        for label, name, address in (
            ("twitter.com regression", "twitter.com", "1.1.1.1"),
            ("example.net regression", "example.net", "3.3.3.3"),
        ):
            check(label, client, "getent hosts {} | grep -q '{}'".format(name, address))
    if host170:
        check("google.com regression", host170, "getent hosts google.com | grep -q '2.2.2.2'")
    if host164:
        check("syr.edu regression", host164, "getent hosts syr.edu | grep -q '128.230.18.63'")
    if ns_example_net and client:
        helper = Path(__file__).resolve().parents[1] / "B02_mini_internet_with_dns" / "add_record.sh"
        if helper.is_file():
            script = helper.read_text(encoding="utf-8")
            check(
                "inherited add_record.sh still updates example.net",
                ns_example_net,
                "cat > /tmp/add_record.sh <<'__SEED_ADD_RECORD_SCRIPT__'\n"
                + script.rstrip()
                + "\n__SEED_ADD_RECORD_SCRIPT__\n"
                "chmod +x /tmp/add_record.sh\n"
                "/tmp/add_record.sh 5.6.7.8",
            )
            wait_check(
                "inherited dynamic record resolves",
                client,
                "getent hosts www.example.net | grep -q '5.6.7.8'",
            )

    test.write_summary("b02a-dynamic-domain-registration-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
