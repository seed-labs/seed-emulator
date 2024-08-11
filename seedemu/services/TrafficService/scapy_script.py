#!/usr/bin/env python3
import threading
import argparse
import time
import ipaddress
from typing import List
from scapy.all import send, IP, ICMP, sr

threads = []


def scan_hosts(networks: List[str]):
    """!
    @brief Scan the networks for active hosts
    @param networks: List[str] - A list of networks to scan
    @return active_hosts: set - A set of active hosts
    """
    time.sleep(60)  # Wait for the network to stabilize
    active_hosts = set()
    for network in networks:
        ans, _ = sr(IP(dst=network) / ICMP(), timeout=10)
        for _, pkt in ans:
            ip_address = pkt[IP].src
            if not ipaddress.ip_address(ip_address) in ipaddress.ip_network(network):
                continue
            if ip_address.endswith(".1") or ip_address.endswith(".254"):
                continue
            active_hosts.add(ip_address)
    return active_hosts


def generate_traffic(source, destination, duration, log_file_name):
    """!
    @brief Generate traffic from source to destination
    @param source: str - Source IP address
    @param destination: str - Destination IP address
    @param duration: int - Duration of the traffic generation (in seconds)
    @param log_file_name: str - Log file name
    """
    t_start = time.time()
    t_end = time.time() + duration
    packet_sent = 0
    while time.time() < t_end:
        send(IP(src=source, dst=destination) / ICMP(), verbose=False)
        packet_sent += 1
        with open(log_file_name, "w") as log_file:
            log_file.write(f"Sending traffic from {source} to {destination}\n")
            log_file.write(f"Duration: {int(time.time()-t_start)}/{duration}\n")
            log_file.write(f"Packet Sent: {packet_sent}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Scapy traffic generator")
    parser.add_argument(
        "-t",
        "--duration",
        type=int,
        default=600,
        help="Duration of the traffic generation (in seconds)",
    )
    parser.add_argument(
        "-l", "--log-prefix", default="/root/scapy-logs", help="Log file prefix"
    )
    args = parser.parse_args()

    main_log_file = open(args.log_prefix + "-main.log", "w")

    networks = []
    with open("/root/traffic-targets", "r") as file:
        networks = [line.strip() for line in file.readlines()]

    main_log_file.write("Scanning networks for active hosts\n")
    main_log_file.flush()
    active_hosts = scan_hosts(networks)
    main_log_file.write("Scan complete\n")
    main_log_file.flush()

    active_hosts = list(active_hosts)

    main_log_file.write(f"Active hosts: {active_hosts}\n")
    main_log_file.flush()

    for i in range(len(active_hosts)):
        for j in range(i + 1, len(active_hosts)):
            main_log_file.write(
                f"Generating traffic from {active_hosts[i]} to {active_hosts[j]}\n"
            )
            main_log_file.write(
                f"Log file: {args.log_prefix}_{active_hosts[i]}_{active_hosts[j]}.log\n"
            )
            main_log_file.flush()

            t = threading.Thread(
                target=generate_traffic,
                args=(
                    active_hosts[i],
                    active_hosts[j],
                    args.duration,
                    f"{args.log_prefix}_{active_hosts[i]}_{active_hosts[j]}.log",
                ),
            )
            threads.append(t)

            main_log_file.write(
                f"Generating traffic from {active_hosts[j]} to {active_hosts[i]}\n"
            )
            main_log_file.write(
                f"Log file: {args.log_prefix}_{active_hosts[j]}_{active_hosts[i]}.log\n"
            )
            main_log_file.flush()

            t = threading.Thread(
                target=generate_traffic,
                args=(
                    active_hosts[j],
                    active_hosts[i],
                    args.duration,
                    f"{args.log_prefix}_{active_hosts[j]}_{active_hosts[i]}.log",
                ),
            )
            threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    main_log_file.close()
