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
traffic_service.install('hybrid-receiver', TrafficServiceType.HYBRID_RECEIVER)
traffic_service.install('hybrid-generator', TrafficServiceType.HYBRID_GENERATOR).addReceivers(hosts=["hybrid-receiver"])

# Add hosts to AS-150
as150 = base.getAutonomousSystem(150)
as150.createHost('hybrid-generator').joinNetwork('net0')


# Add hosts to AS-162 
as162 = base.getAutonomousSystem(162)
as162.createHost('hybrid-receiver').joinNetwork('net0')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('hybrid-generator', filter = Filter(asn = 150, nodeName='hybrid-generator')))
emu.addBinding(Binding('hybrid-receiver', filter = Filter(asn = 162, nodeName='hybrid-receiver')))

# Add the layers
emu.addLayer(traffic_service)
emu.addLayer(etc_hosts)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), './output', override=True)
