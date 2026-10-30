#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    attacker = test.require_service(150, "host_0", "AS150 attacker host is generated")
    victim = test.require_service(151, "host_0", "AS151 victim host is generated")
    victim_router = test.require_service(151, "router0", "AS151 victim access router is generated")
    legitimate_client = test.require_service(153, "host_0", "AS153 legitimate client is generated")
    amplifier0 = test.require_service(152, "host_0", "AS152 amplifier host_0 is generated")
    amplifier11 = test.require_service(152, "host_11", "AS152 amplifier host_11 is generated")
    target_router = test.require_service(152, "router0", "AS152 directed-broadcast router is generated")

    if target_router:
        test.exec_check(
            "AS152 router enables directed broadcast forwarding",
            target_router,
            "test -e /proc/sys/net/ipv4/conf/all/bc_forwarding "
            "&& test \"$(cat /proc/sys/net/ipv4/conf/all/bc_forwarding)\" = 1",
            retries=30,
            interval=3,
        )

    for service in [amplifier0, amplifier11]:
        if service:
            test.exec_check(
                "{} responds to broadcast ICMP echo".format(service.name),
                service,
                "test \"$(cat /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts)\" = 0",
                retries=30,
                interval=3,
            )
            test.exec_check(
                "{} runs the UDP Fraggle amplifier daemon".format(service.name),
                service,
                "pgrep -f 'fraggle_amplifier.py' >/dev/null",
                retries=30,
                interval=3,
            )

    if victim and attacker:
        test.exec_check(
            "victim resets Traffic Visualizer before Smurf validation",
            victim,
            "python3 -c \"import urllib.request; "
            "r=urllib.request.Request('http://127.0.0.1:8080/api/reset', method='POST'); "
            "urllib.request.urlopen(r).read()\"",
            retries=30,
            interval=2,
        )
        test.exec_check(
            "attacker sends spoofed ICMP requests to AS152 directed broadcast",
            attacker,
            "/opt/demo/trigger_attack.sh --count 3 --interval 0.2",
            retries=10,
            interval=2,
        )
        test.exec_check(
            "victim receives multiple reflected ICMP echo replies",
            victim,
            "python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/stats')); "
            "assert d['total_packets'] >= 6, d; "
            "assert d['total_ip_bytes'] >= d['total_packets'] * 28, d\"",
            retries=12,
            interval=1,
        )
        test.exec_check(
            "victim resets Traffic Visualizer before Fraggle validation",
            victim,
            "python3 -c \"import urllib.request; "
            "r=urllib.request.Request('http://127.0.0.1:8080/api/reset', method='POST'); "
            "urllib.request.urlopen(r).read()\"",
            retries=3,
            interval=1,
        )
        test.exec_check(
            "attacker sends spoofed UDP requests to AS152 directed broadcast",
            attacker,
            "/opt/demo/trigger_attack.sh --mode fraggle --count 3 --interval 0.2 --source-port 7000",
            retries=10,
            interval=2,
        )
        test.exec_check(
            "victim receives multiple reflected UDP replies",
            victim,
            "python3 -c \"import json,urllib.request; "
            "d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/stats')); "
            "assert d['total_packets'] >= 6, d; "
            "assert d['total_ip_bytes'] >= d['total_packets'] * 64, d\"",
            retries=12,
            interval=1,
        )

    if victim:
        test.exec_check(
            "victim runs the legitimate HTTP service",
            victim,
            "pgrep -f '/opt/demo/traffic_visualizer/victim_http_service.py' >/dev/null",
            retries=30,
            interval=3,
        )
    if victim_router:
        test.exec_check(
            "victim access router includes the runtime link controller",
            victim_router,
            "test -x /opt/demo/traffic_visualizer/network_control.py",
            retries=1,
            interval=1,
        )

    if legitimate_client:
        test.exec_check(
            "AS153 runs the external victim health probe",
            legitimate_client,
            "pgrep -f '/opt/demo/traffic_visualizer/health_probe.py' >/dev/null",
            retries=30,
            interval=3,
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

    test.write_summary("y11-smurf-attack-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
