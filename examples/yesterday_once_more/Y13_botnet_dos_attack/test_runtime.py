#!/usr/bin/env python3
"""Validate Y13 infrastructure without launching a denial-of-service load."""

from __future__ import annotations

from typing import List

from seedemu.testing import ComposeRuntimeTest, ComposeService
from seedemu.testing.runtime import ADDRESS_LABEL, NODE_LABEL


BOT_CONTROLLER_IP = "10.150.0.66"
EXPECTED_BOT_COUNT = 8


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
    controller = test.require_service(150, "bot-controller", "AS150 BotnetLab controller is generated")
    victim = test.require_service(151, "host_0", "AS151 victim is generated")
    victim_router = test.require_service(151, "router0", "AS151 victim access router is generated")
    legitimate_client = test.require_service(153, "host_0", "AS153 legitimate client is generated")
    bots = discover_bots(test)

    test.structural_check(
        "Y13 creates eight distributed bot clients",
        len(bots) == EXPECTED_BOT_COUNT,
        f"found {len(bots)} bot clients",
    )

    if controller:
        test.structural_check(
            "bot controller uses the expected address",
            controller.address == BOT_CONTROLLER_IP,
            f"controller address={controller.address}",
        )
        test.exec_check(
            "controller runs BotnetLab and provides botctl",
            controller,
            "test -x /opt/botnet-dos/botnet_lab/controller.py && test -x /bin/botctl "
            "&& ps -ef | grep -F '/opt/botnet-dos/botnet_lab/controller.py' "
            "| grep -v grep >/dev/null",
            retries=30,
            interval=2,
        )
        test.exec_check(
            "controller reports all BotnetLab agents online with CORS",
            controller,
            "python3 -c \"import json,urllib.request; "
            "r=urllib.request.urlopen('http://127.0.0.1:8080/api/bots'); "
            "assert r.headers['Access-Control-Allow-Origin'] == '*', r.headers; "
            "d=json.load(r); assert d['bot_count'] == 8, d; "
            "assert d['online_count'] == 8, d\"",
            retries=40,
            interval=2,
        )

    for bot in bots:
        label = bot.labels.get(NODE_LABEL, bot.name)
        test.exec_check(
            f"{label} runs an allowlisted BotnetLab agent",
            bot,
            "test -x /opt/botnet-dos/botnet_lab/agent.py "
            "&& test -x /opt/botnet-dos/bot_attack.py "
            "&& ps -ef | grep -F '/opt/botnet-dos/botnet_lab/agent.py' | grep -v grep >/dev/null "
            "&& python3 /opt/botnet-dos/bot_attack.py --dry-run --json >/dev/null "
            "&& python3 -c \"import urllib.request; "
            "assert urllib.request.urlopen('http://10.150.0.66:8080/healthz').status == 200\"",
            retries=30,
            interval=3,
        )

    if victim:
        test.exec_check(
            "victim UDP sink and HTTP service are running",
            victim,
            "ps -ef | grep -F '/opt/botnet-dos/udp_sink.py' | grep -v grep >/dev/null "
            "&& python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')); "
            "assert d['status'] == 'ok', d\"",
            retries=30,
            interval=2,
        )
        test.exec_check(
            "traffic visualizer serves Y13 configuration",
            victim,
            "python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/config')); "
            "assert d['frontend']['options']['bot_count'] == 8, d\"",
            retries=30,
            interval=2,
        )

    if victim_router:
        test.exec_check(
            "victim access router includes the runtime link controller",
            victim_router,
            "test -x /opt/botnet-dos/traffic_visualizer/network_control.py",
            retries=1,
            interval=1,
        )

    if legitimate_client:
        test.exec_check(
            "health probe API serves latency and goodput samples with CORS",
            legitimate_client,
            "python3 -c \"import json,urllib.request; "
            "r=urllib.request.urlopen('http://127.0.0.1:8080/api/health'); "
            "assert r.headers['Access-Control-Allow-Origin'] == '*', r.headers; "
            "d=json.load(r); assert d['sample_count'] >= 2, d; "
            "assert d['bandwidth_sample_count'] >= 1, d\"",
            retries=30,
            interval=2,
        )

    if controller and bots and victim:
        test.exec_check(
            "controller dispatches a tiny bounded stream through BotnetLab",
            controller,
            "botctl --json launch udp_load --targets bot-000 --start-delay 0 "
            "--timeout 10 --parameters "
            "'{\"duration_seconds\":0.2,\"packets_per_second\":5,\"udp_payload_bytes\":64}' "
            "> /tmp/y13-smoke-command.json "
            "&& command_id=$(python3 -c \"import json; "
            "print(json.load(open('/tmp/y13-smoke-command.json'))['command_id'])\") "
            "&& botctl command \"$command_id\" --watch --interval 0.1 >/dev/null "
            "&& botctl --json command \"$command_id\" "
            "| python3 -c \"import json,sys; d=json.load(sys.stdin); "
            "assert d['status_counts'] == {'completed': 1}, d\"",
            retries=10,
            interval=2,
        )
        test.exec_check(
            "victim visualizer observes the smoke stream",
            victim,
            "python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/stats')); "
            "assert d['total_packets'] >= 1, d\"",
            retries=10,
            interval=1,
        )

    test.write_summary("y13-botnet-dos-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
