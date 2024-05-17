#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
from seedemu.services import TrafficService, TrafficServiceType
from seedemu.layers import EtcHosts
from examples.internet.B00_mini_internet import mini_internet

def run(dumpfile=None):

    emu = Emulator()

    # Run and load the pre-built components
    mini_internet.run(dumpfile='./base-internet.bin')
    emu.load('./base-internet.bin')
    
    base = emu.getLayer('Base')

    traffic_service = TrafficService()
    traffic_service.install(
           'scapy-generator', 
           TrafficServiceType.SCAPY_GENERATOR, 
           log_file="/root/scapy-logs"
    ).addReceivers(hosts=["10.164.0.0/24", "10.170.0.0/24"])

    # Add hosts to AS-150
    as150 = base.getAutonomousSystem(150)
    as150.createHost('scapy-generator').joinNetwork('net0')

    # Binding virtual nodes to physical nodes
    emu.addBinding(Binding('scapy-generator', 
          filter = Filter(asn = 150, nodeName='scapy-generator')))

    # Add the layers
    emu.addLayer(traffic_service)
    emu.addLayer(EtcHosts())
    
    if dumpfile is not None:
       # Save it to a file, so it can be used by other emulators
       emu.dump(dumpfile)
    else:
       # Rendering compilation 
       emu.render()
       emu.compile(Docker(), './output', override=True)

if __name__ == "__main__":
    run()

