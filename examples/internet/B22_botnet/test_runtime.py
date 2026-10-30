#!/usr/bin/env python3
#
# Purpose: validate the running B22 botnet example without scripting the
# interactive BYOB shell. Inputs come from TestRunner environment variables and
# generated docker-compose.yml labels. Outputs are JSON runtime summaries.

from __future__ import annotations

from typing import List

from seedemu.testing import ComposeRuntimeTest, ComposeService
from seedemu.testing.runtime import ADDRESS_LABEL, NODE_LABEL


BOT_CONTROLLER_IP = "10.150.0.66"
EXPECTED_BOT_COUNT = 6


def discover_bots(test: ComposeRuntimeTest) -> List[ComposeService]:
    bots: List[ComposeService] = []
    for name, service in test.compose.get("services", {}).items():
        labels = dict(service.get("labels", {}))
        node_name = str(labels.get(NODE_LABEL, ""))
        if node_name.startswith("bot-node-"):
            address = str(labels.get(ADDRESS_LABEL, "")).split("/", 1)[0]
            bots.append(ComposeService(name=str(name), address=address, labels=labels))

    bots.sort(key=lambda service: str(service.labels.get(NODE_LABEL, service.name)))
    return bots


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    controller = test.require_service(150, "bot-controller")
    bots = discover_bots(test)

    test.structural_check(
        "B22 creates six bot clients",
        len(bots) == EXPECTED_BOT_COUNT,
        "found {} bot clients".format(len(bots)),
    )

    if controller:
        test.structural_check(
            "bot controller uses the expected address",
            controller.address == BOT_CONTROLLER_IP,
            "controller address={}".format(controller.address),
        )
        test.exec_check(
            "controller has BYOB installed",
            controller,
            "test -d /tmp/byob/byob && test -f /tmp/byob/byob/server.py",
            retries=20,
            interval=3,
        )
        test.exec_check(
            "controller has the manual BYOB shell helper",
            controller,
            "test -x /bin/start-byob-shell",
            retries=20,
            interval=3,
        )
        test.exec_check(
            "controller has the DDoS helper script",
            controller,
            "test -f /tmp/ddos.py",
            retries=20,
            interval=3,
        )
        test.exec_check(
            "controller exposes BYOB dropper endpoint",
            controller,
            "curl -fsS http://127.0.0.1:446/clients/droppers/client.py >/dev/null",
            retries=60,
            interval=5,
            timeout=45,
        )

    for bot in bots:
        label = bot.labels.get(NODE_LABEL, bot.name)
        test.exec_check(
            "{} has BYOB client startup runner".format(label),
            bot,
            "test -x /tmp/byob_client_dropper_runner",
            retries=20,
            interval=3,
        )
        test.exec_check(
            "{} reaches controller ICMP".format(label),
            bot,
            "ping -c 3 {} >/dev/null".format(BOT_CONTROLLER_IP),
            retries=30,
            interval=3,
            timeout=45,
        )
        test.exec_check(
            "{} reaches controller dropper HTTP endpoint".format(label),
            bot,
            "curl -fsS http://{}:446/clients/droppers/client.py >/dev/null".format(BOT_CONTROLLER_IP),
            retries=60,
            interval=5,
            timeout=45,
        )

    test.write_summary("b22-botnet-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
