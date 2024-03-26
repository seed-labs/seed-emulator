#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, IperfGenerator, IperfReceiver, HybridTrafficGenerator, HybridTrafficReceiver
from seedemu.layers import EtcHosts

emu = Emulator()
# Load the pre-built mini-internet component
emu.load('../B00-mini-internet/base-component.bin')
base = emu.getLayer('Base')

etc_hosts = EtcHosts()

traffic_service = TrafficService()
traffic_service.addServer('iperf-receiver-1', IperfReceiver())
traffic_service.addServer('iperf-receiver-2', IperfReceiver())
traffic_service.addServer('hybrid-traffic-receiver', HybridTrafficReceiver())

iperf_generator = IperfGenerator(base_layer=base) # TODO: Remove dependency on base_layer
iperf_generator.addTargets(hosts=["iperf-receiver-1", "iperf-receiver-2"])

hybrid_traffic_generator = HybridTrafficGenerator(base_layer=base) # TODO: Remove dependency on base_layer
hybrid_traffic_generator.addTargets(hosts=["hybrid-traffic-receiver"])
hybrid_traffic_generator.addTargets(asns=[154, 171], hosts=["database.com"])


traffic_service.addServer('iperf-generator', iperf_generator)
traffic_service.addServer('hybrid-traffic-generator', hybrid_traffic_generator)
traffic_service.install() # ??


# Create a new host in AS-152 with custom host name
as152 = base.getAutonomousSystem(152)
as152.createHost('database').joinNetwork('net0', address = '10.152.0.4').addHostName('database.com')

# Add hosts to AS-150
as150 = base.getAutonomousSystem(150)
as150.createHost('iperf-generator').joinNetwork('net0').addHostName('iperf-generator')
as150.createHost('hybrid-traffic-generator').joinNetwork('net0').addHostName('hybrid-traffic-generator')

# Add hosts to AS-171 
as171 = base.getAutonomousSystem(171)
as171.createHost('iperf-receiver-1').joinNetwork('net0').addHostName('iperf-receiver-1')
as171.createHost('iperf-receiver-2').joinNetwork('net0').addHostName('iperf-receiver-2')
as171.createHost('hybrid-traffic-receiver').joinNetwork('net0').addHostName('hybrid-traffic-receiver')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('iperf-generator', filter = Filter(asn = 150, nodeName='iperf-generator')))
emu.addBinding(Binding('hybrid-traffic-generator', filter = Filter(asn = 150, nodeName='hybrid-traffic-generator')))
emu.addBinding(Binding('iperf-receiver-1', filter = Filter(asn = 171, nodeName='iperf-receiver-1')))
emu.addBinding(Binding('iperf-receiver-2', filter = Filter(asn = 171, nodeName='iperf-receiver-2')))
emu.addBinding(Binding('hybrid-traffic-receiver', filter = Filter(asn = 171, nodeName='hybrid-traffic-receiver')))

# Add the layers
emu.addLayer(etc_hosts)
emu.addLayer(traffic_service)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), './output', override=True)
