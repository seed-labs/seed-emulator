#!/usr/bin/env python3
#
# Purpose: validate the running B03 hybrid Internet example after TestRunner
# starts Docker Compose. Inputs come from TestRunner environment variables and
# generated docker-compose.yml labels. Outputs are JSON runtime summaries.

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def dockerfiles_containing(test: ComposeRuntimeTest, *patterns: str) -> list[str]:
    matches = []
    for dockerfile in test.compose_file.parent.glob("*/Dockerfile"):
        text = dockerfile.read_text(encoding="utf-8", errors="replace")
        if all(pattern in text for pattern in patterns):
            matches.append(dockerfile.parent.name)
    return sorted(matches)


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    host150 = test.require_service(150, "host_0")
    host152 = test.require_service(152, "host_0")
    host170 = test.require_service(170, "host_0")
    host154_new = test.require_service(154, "host_new")
    syracuse = test.require_service(11872, "rw-11872-syr", "AS11872 real-world router is generated")
    hybrid = test.require_service(99999, "rw-real-world", "AS99999 default real-world gateway is generated")

    if host150 and host152:
        test.exec_check(
            "AS150 reaches AS152 through the reused B00 base",
            host150,
            "ping -c 3 {} >/dev/null".format(host152.address),
            retries=30,
            interval=3,
        )

    if host170 and host154_new:
        test.exec_check(
            "AS170 reaches AS154 customized B00 host",
            host170,
            "ping -c 3 {} >/dev/null".format(host154_new.address),
            retries=30,
            interval=3,
        )

    if syracuse:
        test.exec_check(
            "AS11872 announces the deterministic example prefix",
            syracuse,
            "grep -q '128.230.0.0/16' /etc/bird/bird.conf",
        )
        test.exec_check(
            "AS11872 has real-world router NAT setup",
            syracuse,
            "test -s /rw_configure_script && grep -q 'MASQUERADE' /rw_configure_script",
        )

    if hybrid:
        test.exec_check(
            "AS99999 announces split default prefixes",
            hybrid,
            "grep -q '0.0.0.0/1' /etc/bird/bird.conf && grep -q '128.0.0.0/1' /etc/bird/bird.conf",
        )
        test.exec_check(
            "AS99999 has real-world router NAT setup",
            hybrid,
            "test -s /rw_configure_script && grep -q 'MASQUERADE' /rw_configure_script",
        )

    openvpn_outputs = dockerfiles_containing(test, "/ovpn-server.conf", "/ovpn_startup")
    test.structural_check(
        "OpenVPN remote access bridge is generated for AS152",
        len(openvpn_outputs) >= 1,
        ", ".join(openvpn_outputs),
    )

    test.write_summary("b03-hybrid-internet-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
