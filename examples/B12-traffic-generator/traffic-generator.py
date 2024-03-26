#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, IperfGenerator, IperfReceiver, HybridTrafficGenerator, HybridTrafficReceiver

emu = Emulator()
base = emu.getLayer('Base')

traffic_service = TrafficService()
traffic_service.addServer('iperf-receiver-1', IperfReceiver())
traffic_service.addServer('iperf-receiver-2', IperfReceiver())
traffic_service.addServer('hybrid_traffic_receiver', HybridTrafficReceiver())

iperf_generator = IperfGenerator(base_layer=base) # TODO: Remove dependency on base_layer
iperf_generator.addTargets(hosts=["iperf_receiver_1", "iperf_receiver_2"])

hybrid_traffic_generator = HybridTrafficGenerator(base_layer=base) # TODO: Remove dependency on base_layer
hybrid_traffic_generator.addTargets(hosts=["hybrid_traffic_receiver"])
hybrid_traffic_generator.addTargets(asns=[154, 171], hosts=["database.com"])


traffic_service.addServer('iperf_generator', iperf_generator)
traffic_service.addServer('hybrid_traffic_generator', hybrid_traffic_generator)
traffic_service.install() # TODO: Remove dependency call to install


# Load the pre-built mini-internet component
emu.load('../B00-mini-internet/base-component.bin')


# Create a new host in AS-152 with custom host name
as152 = base.getAutonomousSystem(152)
as152.createHost('database').joinNetwork('net0', address = '10.152.0.4').addHostName('database.com')

# Add hosts to AS-150
as150 = base.getAutonomousSystem(150)
as150.createHost('iperf_generator').joinNetwork('net0').addHostName('iperf_generator')
as150.createHost('hybrid_traffic_generator').joinNetwork('net0').addHostName('hybrid_traffic_generator')

# Add hosts to AS-171 
as171 = base.getAutonomousSystem(171)
as171.createHost('iperf_receiver_1').joinNetwork('net0')
as171.createHost('iperf_receiver_2').joinNetwork('net0')
as171.createHost('hybrid_traffic_receiver').joinNetwork('net0')

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('iperf_generator', filter = Filter(asn = 150, nodeName='iperf_generator')))
emu.addBinding(Binding('hybrid_traffic_generator', filter = Filter(asn = 150, nodeName='hybrid_traffic_generator')))
emu.addBinding(Binding('iperf_receiver_1', filter = Filter(asn = 171, nodeName='iperf_receiver_1')))
emu.addBinding(Binding('iperf_receiver_2', filter = Filter(asn = 171, nodeName='iperf_receiver_2')))
emu.addBinding(Binding('hybrid_traffic_receiver', filter = Filter(asn = 171, nodeName='hybrid_traffic_receiver')))

# Add the traffic_service layer
emu.addLayer(traffic_service)

# Render the emulation and further customization
emu.render()
emu.compile(Docker(), './output', override=True)
