#!/usr/bin/env python3
"""Check A14's generated configuration and live container behavior."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    services = test.compose.get("services", {})
    app = "demo-app.demo.seed"
    helper = "demo-helper.demo.seed"
    expected_networks = {
        app: {
            "demo_bundle_network": {"ipv4_address": "172.31.0.10"},
            "net_151_net0": {"ipv4_address": "10.151.0.16"},
            "net_152_net0": {"ipv4_address": "10.152.0.16"},
        },
        helper: {"demo_bundle_network": {"ipv4_address": "172.31.0.11"}},
    }
    # Prepared containers have no Base-node labels; their suffixed service keys
    # are the public identifiers used by this example.
    for name, networks in expected_networks.items():
        config = services.get(name, {})
        test.structural_check(
            f"{name} has its static network attachments",
            config.get("networks") == networks,
            str(config.get("networks")),
        )
        test.structural_check(
            f"{name} has the expected container name and wrapper",
            config.get("container_name") == name
            and config.get("entrypoint") == ["sh", "/new-entrypoint.sh"],
            str({key: config.get(key) for key in ("container_name", "entrypoint")}),
        )

    ports = services.get(app, {}).get("ports", [])
    test.structural_check("app publishes 8090 to 8080", "8090:8080" in ports, str(ports))
    ipam = test.compose.get("networks", {}).get("demo_bundle_network", {}).get("ipam", {})
    test.structural_check(
        "bridge has its explicit subnet and gateway",
        {"subnet": "172.31.0.0/24", "gateway": "172.31.0.1"} in ipam.get("config", []),
        str(ipam),
    )

    if app in services:
        test.exec_check(
            "app resolves helper through its shared hosts alias",
            app,
            "getent ahostsv4 demo-helper-demo_bundle_network "
            "| awk '$1 == \"172.31.0.11\" {found=1} END {exit !found}'",
            retries=8, interval=2, timeout=15,
        )
        test.exec_check(
            "staged script is executable and prints the demo message",
            app,
            "test -x /usr/local/bin/demo-message.sh "
            "&& /usr/local/bin/demo-message.sh | grep -Fxq 'ContainerBundle demo is running'",
            retries=8, interval=2, timeout=15,
        )
        test.exec_check(
            "app has both internal addresses and the first gateway",
            app,
            "ip -o -4 addr show | grep -Fq '10.151.0.16/' "
            "&& ip -o -4 addr show | grep -Fq '10.152.0.16/' "
            "&& ip -4 route show default | grep -Fq 'via 10.151.0.254 '",
            retries=8, interval=2, timeout=15,
        )
        for gateway in ("10.151.0.254", "10.152.0.254"):
            test.exec_check(
                f"app reaches emulator gateway {gateway}", app,
                f"ping -c 2 -W 2 {gateway} >/dev/null",
                retries=8, interval=2, timeout=15,
            )
    if helper in services:
        test.exec_check(
            "helper resolves and reaches app over the private bridge",
            helper,
            "getent ahostsv4 demo-app-demo_bundle_network "
            "| awk '$1 == \"172.31.0.10\" {found=1} END {exit !found}' "
            "&& ping -c 2 -W 2 demo-app-demo_bundle_network >/dev/null",
            retries=8, interval=2, timeout=15,
        )
        test.exec_check(
            "helper also receives the app's shared internal alias",
            helper,
            "getent ahostsv4 demo-app.demo.seed "
            "| awk '$1 == \"10.151.0.16\" {found=1} END {exit !found}'",
            retries=8, interval=2, timeout=15,
        )

    # Port 8090 is a mapping demonstration; this example starts no HTTP server.
    test.write_summary("a14-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
