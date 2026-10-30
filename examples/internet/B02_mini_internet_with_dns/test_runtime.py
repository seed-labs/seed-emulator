#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    local_dns_1 = test.require_service(152, "local-dns-1")
    local_dns_2 = test.require_service(153, "local-dns-2")
    host150 = test.require_service(150, "host_0")
    host160 = test.require_service(160, "host_0")
    ns_example_net = test.require_service(163, "host_0", "example.net authoritative server is generated")
    host164 = test.require_service(164, "host_0")
    host170 = test.require_service(170, "host_0")
    add_record = Path(__file__).resolve().parent / "add_record.sh"

    test.structural_check(
        "add_record.sh helper exists for dynamic DNS updates",
        add_record.is_file(),
        "found {}".format(add_record),
    )

    if local_dns_1:
        test.structural_check(
            "AS152 local DNS cache has the expected fixed address",
            local_dns_1.address == "10.152.0.53",
            "observed {}".format(local_dns_1.address),
        )
        test.exec_check("AS152 local DNS cache is running named", local_dns_1, "pgrep named >/dev/null")

    if local_dns_2:
        test.structural_check(
            "AS153 local DNS cache has the expected fixed address",
            local_dns_2.address == "10.153.0.53",
            "observed {}".format(local_dns_2.address),
        )
        test.exec_check("AS153 local DNS cache is running named", local_dns_2, "pgrep named >/dev/null")

    if host160:
        test.exec_check(
            "AS160 host uses global-dns-1",
            host160,
            "grep -q 'nameserver[[:space:]]*10.152.0.53' /etc/resolv.conf",
        )
        test.exec_check(
            "AS160 resolves twitter.com from the B01 DNS component",
            host160,
            "getent hosts twitter.com | grep -q '1.1.1.1'",
        )

    if host170:
        test.exec_check(
            "AS170 host uses global-dns-1",
            host170,
            "grep -q 'nameserver[[:space:]]*10.152.0.53' /etc/resolv.conf",
        )
        test.exec_check(
            "AS170 resolves google.com from the B01 DNS component",
            host170,
            "getent hosts google.com | grep -q '2.2.2.2'",
        )

    if host150:
        test.exec_check(
            "AS150 host uses global-dns-2 by default",
            host150,
            "grep -q 'nameserver[[:space:]]*10.153.0.53' /etc/resolv.conf",
        )
        test.exec_check(
            "AS150 resolves example.net from the B01 DNS component",
            host150,
            "getent hosts example.net | grep -q '3.3.3.3'",
        )

    if host164:
        test.exec_check(
            "AS164 host uses global-dns-2 by default",
            host164,
            "grep -q 'nameserver[[:space:]]*10.153.0.53' /etc/resolv.conf",
        )
        test.exec_check(
            "AS164 resolves syr.edu from the B01 DNS component",
            host164,
            "getent hosts syr.edu | grep -q '128.230.18.63'",
        )

    if ns_example_net and host150 and add_record.is_file():
        script_text = add_record.read_text(encoding="utf-8")
        if not script_text.endswith("\n"):
            script_text += "\n"
        run_add_record = (
            "cat > /tmp/add_record.sh <<'__SEED_ADD_RECORD_SCRIPT__'\n"
            "{}"
            "__SEED_ADD_RECORD_SCRIPT__\n"
            "chmod +x /tmp/add_record.sh\n"
            "/tmp/add_record.sh 5.6.7.8"
        ).format(script_text)
        test.exec_check(
            "add_record.sh dynamically adds www.example.net",
            ns_example_net,
            run_add_record,
        )
        test.exec_check(
            "AS150 resolves dynamically added www.example.net record",
            host150,
            "getent hosts www.example.net | grep -q '5.6.7.8'",
        )

    test.write_summary("b02-dns-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
