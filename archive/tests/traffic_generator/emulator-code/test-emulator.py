#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
from examples.internet.B00_mini_internet import mini_internet

# Run the pre-built components
mini_internet.run(dumpfile='./base-internet.bin')
emu = Emulator()
# Load the pre-built mini-internet component
emu.load("./base-internet.bin")
base = emu.getLayer("Base")

etc_hosts = EtcHosts()

traffic_service = TrafficService()
traffic_service.install("iperf-receiver-1", TrafficServiceType.IPERF_RECEIVER)
traffic_service.install("iperf-receiver-2", TrafficServiceType.IPERF_RECEIVER)
traffic_service.install(
    "iperf-generator",
    TrafficServiceType.IPERF_GENERATOR,
    log_file="/root/iperf3_generator.log",
    protocol="TCP",
    duration=600,
    rate=0,
).addReceivers(hosts=["iperf-receiver-1", "iperf-receiver-2"])

traffic_service.install("ditg-receiver", TrafficServiceType.DITG_RECEIVER)
traffic_service.install(
    "ditg-generator",
    TrafficServiceType.DITG_GENERATOR,
    log_file="/root/ditg_generator.log",
    protocol="TCP",
    duration=600,
    rate=5000,
).addReceivers(hosts=["ditg-receiver"])
traffic_service.install('scapy-generator', TrafficServiceType.SCAPY_GENERATOR, log_file="/root/scapy-logs").addReceivers(hosts=["10.164.0.0/24", "10.170.0.0/24"])
traffic_service.install("multi-traffic-receiver", TrafficServiceType.DITG_RECEIVER)
traffic_service.install("multi-traffic-receiver", TrafficServiceType.IPERF_RECEIVER)
traffic_service.install(
    "multi-traffic-generator",
    TrafficServiceType.DITG_GENERATOR,
    log_file="/root/ditg_generator.log",
    protocol="UDP",
    duration=120,
    rate=5000,
).addReceivers(hosts=["multi-traffic-receiver"])
traffic_service.install(
    "multi-traffic-generator",
    TrafficServiceType.IPERF_GENERATOR,
    log_file="/root/iperf3_generator.log",
    protocol="TCP",
    duration=600,
    rate=0,
).addReceivers(hosts=["multi-traffic-receiver"])

# Add hosts to AS-150
as150 = base.getAutonomousSystem(150)
as150.createHost("iperf-generator").joinNetwork("net0")
as150.createHost("ditg-generator").joinNetwork("net0")
as150.createHost('scapy-generator').joinNetwork('net0')
as150.createHost('multi-traffic-generator').joinNetwork('net0')

# Add hosts to AS-162
as162 = base.getAutonomousSystem(162)
as162.createHost("iperf-receiver-1").joinNetwork("net0")
as162.createHost("ditg-receiver").joinNetwork("net0")
as162.createHost('multi-traffic-receiver').joinNetwork('net0')

# Add hosts to AS-171
as171 = base.getAutonomousSystem(171)
as171.createHost("iperf-receiver-2").joinNetwork("net0")

# Binding virtual nodes to physical nodes
emu.addBinding(
    Binding("iperf-generator", filter=Filter(asn=150, nodeName="iperf-generator"))
)
emu.addBinding(
    Binding("iperf-receiver-1", filter=Filter(asn=162, nodeName="iperf-receiver-1"))
)
emu.addBinding(
    Binding("iperf-receiver-2", filter=Filter(asn=171, nodeName="iperf-receiver-2"))
)
emu.addBinding(
    Binding("ditg-generator", filter=Filter(asn=150, nodeName="ditg-generator"))
)
emu.addBinding(
    Binding("ditg-receiver", filter=Filter(asn=162, nodeName="ditg-receiver"))
)
emu.addBinding(Binding('scapy-generator', filter = Filter(asn = 150, nodeName='scapy-generator')))
emu.addBinding(Binding('multi-traffic-generator', filter = Filter(asn = 150, nodeName='multi-traffic-generator')))
emu.addBinding(Binding('multi-traffic-receiver', filter = Filter(asn = 162, nodeName='multi-traffic-receiver')))


# Add the layers
emu.addLayer(traffic_service)
emu.addLayer(etc_hosts)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), "./output")
