#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from seedemu.testing import ComposeRuntimeTest


POLICY_PATH = "/opt/seedemu-agent-registrar/policy.json"


def main() -> int:
    test = ComposeRuntimeTest(__file__)
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
        test.exec_check(
            "registrar container receives the dynamic TLD policy",
            registrar,
            "test -r {} && grep -q '\"com\"' {} "
            "&& grep -q 'ns1.seedemu-dns.net' {} "
            "&& grep -q 'ns2.seedemu-dns.net' {}".format(
                POLICY_PATH, POLICY_PATH, POLICY_PATH, POLICY_PATH
            ),
        )
        test.exec_check(
            "an unclaimed valid .com domain is available",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com/availability "
            "| grep -q '\"available\":true'",
        )
        test.exec_check(
            "purchase atomically creates a provisioning order",
            registrar,
            "curl -fsS -X POST http://127.0.0.1:8080/v1/purchases "
            "-H 'Content-Type: application/json' -H 'Idempotency-Key: b02a-alice' "
            "--data '{\"domain\":\"alice-shop.com\","
            "\"registrant_id\":\"alice\",\"years\":1}' "
            "| grep -q '\"status\":\"provisioning\"'",
        )
        test.exec_check(
            "a claimed domain is no longer available",
            registrar,
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com/availability "
            "| grep -q '\"available\":false'",
        )
        test.exec_check(
            "outbox provisions the zone, delegation, and activates the order",
            registrar,
            "for i in $(seq 1 40); do "
            "curl -fsS http://127.0.0.1:8080/v1/domains/alice-shop.com "
            "| grep -q '\"status\":\"active\"' && exit 0; sleep 1; done; exit 1",
        )
        test.exec_check(
            "owner can add an A record through the managed DNS API",
            registrar,
            "curl -fsS -X PUT http://127.0.0.1:8080/v1/domains/alice-shop.com/records/www-a "
            "-H 'Content-Type: application/json' --data '{\"registrant_id\":\"alice\","
            "\"name\":\"www.alice-shop.com\",\"record_type\":\"A\","
            "\"ttl\":30,\"value\":\"10.150.0.71\"}' >/dev/null; "
            "for i in $(seq 1 40); do curl -fsS "
            "-H 'X-Registrant-ID: alice' "
            "http://127.0.0.1:8080/v1/domains/alice-shop.com/records "
            "| grep -q '\"status\":\"active\"' && exit 0; sleep 1; done; exit 1",
        )
        test.exec_check(
            "non-owner managed DNS write is rejected",
            registrar,
            "test \"$(curl -sS -o /tmp/non-owner.json -w '%{http_code}' -X PUT "
            "http://127.0.0.1:8080/v1/domains/alice-shop.com/records/intruder "
            "-H 'Content-Type: application/json' --data '{\"registrant_id\":\"mallory\","
            "\"name\":\"bad.alice-shop.com\",\"record_type\":\"A\","
            "\"ttl\":30,\"value\":\"10.150.0.71\"}')\" = 403 "
            "&& grep -q 'not_domain_owner' /tmp/non-owner.json",
        )

    expected_delegation = (
        "test \"$(dig +noall +authority @{} alice-shop.com NS "
        "| awk '$4 == \\\"NS\\\" {{print $5}}' | sort | tr '\\n' ' ')\" = "
        "\"ns1.seedemu-dns.net. ns2.seedemu-dns.net. \""
    )
    if com_master:
        test.exec_check(
            "com master contains the new delegation",
            com_master,
            expected_delegation.format("127.0.0.1"),
        )
    if com_secondary:
        test.exec_check(
            "com secondary received the delegation through zone transfer",
            com_secondary,
            expected_delegation.format("127.0.0.1"),
        )

    if managed_dns_master:
        test.structural_check(
            "managed DNS master has the expected fixed address",
            managed_dns_master.address == "10.161.0.53",
            "observed {}".format(managed_dns_master.address),
        )
        test.exec_check(
            "managed DNS master is running named",
            managed_dns_master,
            "pgrep named >/dev/null",
        )
        test.exec_check(
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
        test.exec_check(
            "managed DNS secondary is running named",
            managed_dns_secondary,
            "pgrep named >/dev/null",
        )
        test.exec_check(
            "managed DNS secondary received the zone and record through AXFR",
            managed_dns_secondary,
            "test \"$(dig +short @127.0.0.1 www.alice-shop.com A)\" = \"10.150.0.71\"",
        )

    if client:
        test.exec_check(
            "managed DNS provider names resolve through the DNS hierarchy",
            client,
            "test \"$(dig +short ns1.seedemu-dns.net A)\" = \"10.161.0.53\" "
            "&& test \"$(dig +short ns2.seedemu-dns.net A)\" = \"10.162.0.53\"",
        )

    if client:
        test.exec_check(
            "recursive DNS resolves the separately added application A record",
            client,
            "test \"$(dig +short www.alice-shop.com A)\" = \"10.150.0.71\"",
        )

        for label, name, address in (
            ("twitter.com regression", "twitter.com", "1.1.1.1"),
            ("example.net regression", "example.net", "3.3.3.3"),
        ):
            test.exec_check(label, client, "getent hosts {} | grep -q '{}'".format(name, address))
    if host170:
        test.exec_check("google.com regression", host170, "getent hosts google.com | grep -q '2.2.2.2'")
    if host164:
        test.exec_check("syr.edu regression", host164, "getent hosts syr.edu | grep -q '128.230.18.63'")
    if ns_example_net and client:
        helper = Path(__file__).resolve().parents[1] / "B02_mini_internet_with_dns" / "add_record.sh"
        if helper.is_file():
            script = helper.read_text(encoding="utf-8")
            test.exec_check(
                "inherited add_record.sh still updates example.net",
                ns_example_net,
                "cat > /tmp/add_record.sh <<'EOF'\n" + script.rstrip() +
                "\nEOF\nchmod +x /tmp/add_record.sh\n/tmp/add_record.sh 5.6.7.8",
            )
            test.exec_check("inherited dynamic record resolves", client,
                            "getent hosts www.example.net | grep -q '5.6.7.8'")

    test.write_summary("b02a-dynamic-domain-registration-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
