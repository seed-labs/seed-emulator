#!/usr/bin/env python3
import threading
import argparse
from scapy.all import send, IP, ICMP, sniff, sr

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
        sr(IP(src=host_a, dst=host_b)/ICMP())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traffic generator")
    parser.add_argument("--networks", nargs="+", help="Networks to scan")
    args = parser.parse_args()
    # ["10.162.0.0/24", "10.150.0.0/24"]
    # scan_hosts(args.networks)

    scan_hosts(["10.162.0.0/24", "10.150.0.0/24"])
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

