from __future__ import annotations
from seedemu.core import Node, Service, Server
# from typing import Dict



class TrafficServer(Server):
    """!
    @brief The TrafficServer class.
    """
    def __init__(self):
        """!
        @brief TrafficServer constructor.
        """
        super().__init__()

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addSoftware('iperf3')
        node.appendStartCommand('iperf3 -s -D')
        node.appendClassName("TrafficService")
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Traffic server object.\n'

        return out

class TrafficService(Service):
    """!
    @brief The TrafficService class.
    """

    def __init__(self):
        """!
        @brief TrafficService constructor.
        """
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return TrafficServer()

    def getName(self) -> str:
        return 'TrafficService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficServiceLayer\n'

        return out


class TrafficGeneratorServer(Server):
    """!
    @brief The TrafficGeneratorServer class.
    """
    def __init__(self, networks=None):
        """!
        @brief TrafficGeneratorServer constructor.
        """
        self.__networks = networks
        self.__traffic_generator = """#!/usr/bin/env python3
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
        print(f"Sending traffic from {host_a} to {host_b}")
        sr(IP(src=host_a, dst=host_b)/ICMP(), timeout=10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traffic generator")
    parser.add_argument("--networks", nargs="+", help="Networks to scan")
    args = parser.parse_args()
    # ["10.162.0.0/24", "10.150.0.0/24"]
    # scan_hosts(args.networks)

    scan_hosts(["10.162.0.0/24", "10.150.0.0/24"])
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
"""
        super().__init__()

    def install(self, node: Node):
        """!
        @brief Install the service.
        """
        node.addSoftware('iperf3')
        node.addSoftware('python3')
        node.addSoftware('python3-pip')
        node.addSoftware('arp-scan')
        node.addSoftware('nmap')
        node.addBuildCommand('pip3 install scapy==2.5.0')

        node.setFile('/root/traffic_generator.py', self.__traffic_generator)
        node.appendStartCommand('chmod +x /root/traffic_generator.py')
        node.appendStartCommand('/root/traffic_generator.py > /root/traffic.log')

        node.appendClassName("TrafficGeneratorService")
        
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGenerator server object.\n'

        return out

class TrafficGeneratorService(Service):
    """!
    @brief The TrafficGeneratorService class.
    """

    def __init__(self, networks=None):
        """!
        @brief TrafficGeneratorService constructor.
        networks: comma separated list of networks to scan.
        """
        self.networks = networks
        super().__init__()
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return TrafficGeneratorServer(self.networks)

    def getName(self) -> str:
        return 'TrafficGeneratorService'

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'TrafficGeneratorServiceLayer\n'

        return out
