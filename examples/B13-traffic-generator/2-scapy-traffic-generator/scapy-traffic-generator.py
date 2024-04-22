#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts

emu = Emulator()
# Load the pre-built mini-internet component
emu.load('../../B00-mini-internet/base-component.bin')
base = emu.getLayer('Base')

etc_hosts = EtcHosts()

traffic_service = TrafficService()
traffic_service.install('scapy-generator', TrafficServiceType.SCAPY_GENERATOR, log_file="/root/scapy-logs").addReceivers(hosts=["10.164.0.0/24", "10.170.0.0/24"])

# Add hosts to AS-150
as150 = base.getAutonomousSystem(150)
as150.createHost('scapy-generator').joinNetwork('net0')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('scapy-generator', filter = Filter(asn = 150, nodeName='scapy-generator')))

# Add the layers
emu.addLayer(traffic_service)
emu.addLayer(etc_hosts)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), './output', override=True)
