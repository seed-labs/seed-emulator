#!/usr/bin/env python3
import threading
import argparse
from scapy.all import send, IP, ICMP, sr

active_hosts = set()
threads = []

def scan_hosts(networks):
    for network in networks:
        ans, _ = sr(IP(dst=network)/ICMP(), timeout=10)
        for _, pkt in ans:
            ip_address = pkt[IP].src
            active_hosts.add(ip_address)


def generate_traffic(host_a, host_b):
    while True:
        print(f"Sending traffic from {{host_a}} to {{host_b}}")
        send(IP(src=host_a, dst=host_b)/ICMP())

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Scapy traffic generator")
    parser.add_argument("networks", nargs="+", help="Networks to scan for active hosts")
    args = parser.parse_args()
    scan_hosts(args.networks)
    active_hosts = list(active_hosts)
    for i in range(len(active_hosts)):
        for j in range(i+1, len(active_hosts)):
            t = threading.Thread(target=generate_traffic, args=(active_hosts[i], active_hosts[j]))
            threads.append(t)
            t = threading.Thread(target=generate_traffic, args=(active_hosts[j], active_hosts[i]))
            threads.append(t)
    print(active_hosts)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
