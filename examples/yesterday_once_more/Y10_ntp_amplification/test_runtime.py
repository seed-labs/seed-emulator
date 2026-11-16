#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


AMPLIFIERS = ["10.152.0.71", "10.160.0.71", "10.171.0.71"]
VICTIM_LOG = "/var/log/ntp-like-victim.log"


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    attacker = test.require_service(150, "host_0", "AS150 attacker host is generated")
    victim = test.require_service(151, "host_0", "AS151 victim host is generated")
    victim_router = test.require_service(151, "router0", "AS151 victim access router is generated")
    legitimate_client = test.require_service(153, "host_0", "AS153 legitimate client is generated")
    amplifier152 = test.require_service(152, "host_0", "AS152 amplifier host is generated")
    amplifier160 = test.require_service(160, "host_0", "AS160 amplifier host is generated")
    amplifier171 = test.require_service(171, "host_0", "AS171 amplifier host is generated")

    if attacker:
        test.exec_check(
            "attacker direct queries receive amplified responses",
            attacker,
            "/opt/ntp-like/trigger_attack.py --interval 0 --json",
            retries=30,
            interval=3,
        )

    if victim:
        test.exec_check(
            "victim UDP sink is running",
            victim,
            "ps -ef | grep -F '/opt/ntp-like/udp_sink.py' | grep -v grep >/dev/null",
            retries=30,
            interval=3,
        )
        test.exec_check(
            "victim HTTP service responds",
            victim,
            "python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')); "
            "assert d['status'] == 'ok', d\"",
            retries=30,
            interval=2,
        )
    if victim_router:
        test.exec_check(
            "victim access router includes the runtime link controller",
            victim_router,
            "test -x /opt/ntp-like/traffic_visualizer/network_control.py",
            retries=1,
            interval=1,
        )

    if legitimate_client:
        test.exec_check(
            "legitimate client runs the health probe",
            legitimate_client,
            "ps -ef | grep -F '/opt/ntp-like/traffic_visualizer/health_probe.py' | grep -v grep >/dev/null",
            retries=30,
            interval=2,
        )

    if legitimate_client:
        test.exec_check(
            "health probe API serves latency and goodput samples with CORS",
            legitimate_client,
            "python3 -c \"import json,urllib.request; "
            "r=urllib.request.urlopen('http://127.0.0.1:8080/api/health'); "
            "assert r.headers['Access-Control-Allow-Origin'] == '*', r.headers; "
            "d=json.load(r); "
            "assert d['sample_count'] >= 2, d; "
            "assert d['bandwidth_sample_count'] >= 1, d; "
            "assert d['latest_throughput_mbps'] is not None, d\"",
            retries=30,
            interval=2,
        )

    if attacker and victim:
        test.exec_check(
            "reflection simulation sends amplifier responses to victim",
            victim,
            f": > {VICTIM_LOG}",
            retries=1,
            interval=1,
        )
        test.exec_check(
            "attacker triggers reflection simulation",
            attacker,
            "/opt/ntp-like/trigger_attack.py --reflect --rounds 2 --interval 0.05 --json",
            retries=10,
            interval=2,
        )
        test.exec_check(
            "victim receives reflected UDP amplification traffic",
            victim,
            "sleep 2; test $(wc -l < {}) -ge 6 && awk -F'bytes=' '{{sum += $2}} END {{exit !(sum >= 6000)}}' {}".format(
                VICTIM_LOG,
                VICTIM_LOG,
            ),
            retries=10,
            interval=2,
        )

    for service in [amplifier152, amplifier160, amplifier171]:
        if service:
            test.exec_check(
                "{} runs the NTP-like daemon".format(service.name),
                service,
                "ps -ef | grep -F '/opt/ntp-like/ntp_like_daemon.py' | grep -v grep >/dev/null",
                retries=30,
                interval=3,
            )

    test.write_summary("y10-ntp-amplification-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
