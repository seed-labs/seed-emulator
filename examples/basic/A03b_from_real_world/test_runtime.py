#!/usr/bin/env python3

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

    web151 = test.require_service(151, "web")
    web152 = test.require_service(152, "web")

    if web151 and web152:
        test.exec_check("AS151 fetches AS152 web service", web151, "curl -fsS http://{} >/dev/null".format(web152.address))
        test.exec_check("AS152 fetches AS151 web service", web152, "curl -fsS http://{} >/dev/null".format(web151.address))

    openvpn_outputs = dockerfiles_containing(test, "/ovpn-server.conf", "/ovpn_startup")
    test.structural_check(
        "OpenVPN bridge nodes are generated",
        len(openvpn_outputs) >= 2,
        ", ".join(openvpn_outputs),
    )

    real_world_outputs = dockerfiles_containing(test, "/rw_configure_script")
    test.structural_check(
        "Real-world router is absent from from-real-world example",
        not real_world_outputs,
        ", ".join(real_world_outputs),
    )

    test.write_summary("a03b-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
